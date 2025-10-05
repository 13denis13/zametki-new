from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()
engine = create_engine(os.getenv("DATABASE"))
Session = sessionmaker(bind=engine)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    type = Column(String) 
    description = Column(String, default="")
    category = Column(String, default="")
    date = Column(DateTime(timezone=True), default=datetime.now(pytz.timezone('Europe/Moscow')))

Base.metadata.create_all(engine)

async def init_db():
    Base.metadata.create_all(engine)

async def add_transaction(user_id, amount, tr_type, description="", category=""):
    with Session() as session:
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=tr_type,
            description=description,
            category=category
        )
        session.add(transaction)
        session.commit()

async def get_weekly_stats(user_id):
    timezone = pytz.timezone('Europe/Moscow')
    now = datetime.now(timezone)
    week_ago = now - timedelta(days=7)

    with Session() as session:
        income = session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'income',
            Transaction.date >= week_ago
        ).scalar() or 0

        expense = session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= week_ago
        ).scalar() or 0

        return {
            'income': income,
            'expense': expense
        }

async def get_weekly_transactions(user_id):
    timezone = pytz.timezone('Europe/Moscow')
    now = datetime.now(timezone)
    week_ago = now - timedelta(days=7)

    with Session() as session:
        transactions = session.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= week_ago
        ).order_by(Transaction.date.desc()).all()

        return transactions

async def get_categories_for_user(user_id):
    with Session() as session:
        categories = session.query(Transaction.category).filter(
            Transaction.user_id == user_id,
            Transaction.category != ""
        ).distinct().all()
        return [cat[0] for cat in categories]

async def get_transactions_by_category(user_id, category, start_date):
    timezone = pytz.timezone('Europe/Moscow')
    with Session() as session:
        transactions = session.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == category,
            Transaction.date >= start_date
        ).order_by(Transaction.date.desc()).all()

        return transactions

async def delete_user_data(user_id):
    with Session() as session:
        count = session.query(Transaction).filter_by(user_id=user_id).delete()
        session.commit()
        return count

async def send_weekly_reports(bot):
    timezone = pytz.timezone('Europe/Moscow')
    now = datetime.now(timezone)
    week_ago = now - timedelta(days=7)

    with Session() as session:
        users = session.query(Transaction.user_id).distinct().all()

        for user_id in users:
            try:
                stats = await get_weekly_stats(user_id[0])
                total_income = stats.get('income', 0)
                total_expense = stats.get('expense', 0)
                balance = total_income - total_expense

                report = (
                    f"🗓 Отчет с {week_ago.strftime('%d.%m')} по {now.strftime('%d.%m')}:\n\n"
                    f"🟢 Доходы: {total_income:.2f} ₽\n"
                    f"🔴 Расходы: {total_expense:.2f} ₽\n"
                    f"⚖️ Баланс: {balance:.2f} ₽"
                )

                last_ops = session.query(Transaction).filter(
                    Transaction.user_id == user_id[0],
                    Transaction.date >= week_ago
                ).order_by(Transaction.date.desc()).limit(3).all()

                if last_ops:
                    report += "\n\nПоследние операции:"
                    for op in last_ops:
                        report += f"\n• {op.date.astimezone(timezone).strftime('%d.%m %H:%M')} - {op.amount:.2f} ₽ ({op.type}) - {op.description or 'Без описания'} ({op.category or 'Без категории'})"

                await bot.send_message(chat_id=user_id[0], text=report)

            except Exception as e:
                print(f"Ошибка отправки отчета для {user_id[0]}: {str(e)}")