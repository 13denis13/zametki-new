from aiogram import Router, F
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards.inline_kb import main_kb,back_kb, confirm_delete_kb, categories_kb, report_category_kb, ask_description_kb, report_kb
from app.baza.database import add_transaction, get_weekly_stats, get_weekly_transactions, get_categories_for_user, get_transactions_by_category, delete_user_data
import re
import asyncio
from datetime import datetime, timedelta
import pytz

router = Router()

class TransactionStates(StatesGroup):
    AMOUNT = State()
    CATEGORY = State()
    ASK_DESCRIPTION = State()
    DESCRIPTION = State()

class DeleteStates(StatesGroup):
    CONFIRM = State()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    await asyncio.sleep(1)
    user = message.from_user
    name = user.full_name or user.username or "пользователь"
    await message.answer(
        f"Привет, {name}! 🤙\n\n"
        "Это ваш персональный финансовый трекер 📊\n"
        "Начните с добавления первой операции:",
        reply_markup=main_kb()
    )

@router.callback_query(F.data.in_(["income", "expense"]))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(type=callback.data)
    await callback.message.edit_text("Введите сумму: ")
    await callback.answer("Выбран тип операции")
    await state.set_state(TransactionStates.AMOUNT)

@router.message(TransactionStates.AMOUNT)
async def process_amount(message: Message, state: FSMContext):
    if not re.match(r"^\d+([.,]\d{1,2})?$", message.text):
        return await message.answer("Некорректная сумма! Пример: 1500.50")

    amount = float(message.text.replace(',', '.'))
    await state.update_data(amount=amount)
    data = await state.get_data()
    kb = categories_kb(data['type'])
    await message.answer("Выберите категорию:", reply_markup=kb)
    await state.set_state(TransactionStates.CATEGORY)

@router.callback_query(F.data == "back", TransactionStates.AMOUNT)
async def back_to_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите тип операции:", reply_markup=main_kb())
    await state.clear()

@router.callback_query(F.data.startswith("cat_"), TransactionStates.CATEGORY)
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "").replace("_", " ").title()
    await state.update_data(category=category)
    await callback.message.edit_text(
        f"Категория: {category}\n\nХотите добавить описание?",
        reply_markup=ask_description_kb()
    )
    await state.set_state(TransactionStates.ASK_DESCRIPTION)

@router.callback_query(F.data == "back", TransactionStates.CATEGORY)
async def back_to_amount(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text("Введите сумму:", reply_markup=back_kb())
    await state.set_state(TransactionStates.AMOUNT)

@router.callback_query(F.data == "back", TransactionStates.ASK_DESCRIPTION)
async def back_to_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    kb = categories_kb(data['type'])
    await callback.message.edit_text("Выберите категорию:", reply_markup=kb)
    await state.set_state(TransactionStates.CATEGORY)

@router.callback_query(F.data.in_(["desc_yes", "desc_no"]), TransactionStates.ASK_DESCRIPTION)
async def ask_description(callback: CallbackQuery, state: FSMContext):
    if callback.data == "desc_yes":
        await callback.message.edit_text("Введите описание:", reply_markup=back_kb())
        await state.set_state(TransactionStates.DESCRIPTION)
    elif callback.data == "desc_no":
        data = await state.get_data()
        await add_transaction(
            user_id=callback.from_user.id,
            amount=data['amount'],
            tr_type=data['type'],
            category=data['category']
        )
        await callback.message.edit_text(
            f"✅ Операция сохранена!\nСумма: {data['amount']}\nКатегория: {data['category']}",
            reply_markup=main_kb()
        )
        await state.clear()

@router.callback_query(F.data == "back", TransactionStates.DESCRIPTION)
async def back_to_ask_description(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        f"Категория: {data['category']}\n\nХотите добавить описание?",
        reply_markup=ask_description_kb()
    )
    await state.set_state(TransactionStates.ASK_DESCRIPTION)

@router.message(TransactionStates.DESCRIPTION)
async def process_description(message: Message, state: FSMContext):
    description = message.text
    data = await state.get_data()

    await add_transaction(
        user_id=message.from_user.id,
        amount=data['amount'],
        tr_type=data['type'],
        description=description,
        category=data['category']
    )

    await message.answer(
        f"✅ Операция сохранена!\nСумма: {data['amount']}\nКатегория: {data['category']}\nОписание: {description}",
        reply_markup=main_kb()
    )
    await state.clear()

@router.callback_query(F.data == "report")
async def show_report(callback: CallbackQuery):
    timezone = pytz.timezone('Europe/Moscow')
    now = datetime.now(timezone)
    week_ago = now - timedelta(days=7)

    stats = await get_weekly_stats(callback.from_user.id)
    transactions = await get_weekly_transactions(callback.from_user.id)

    total_income = stats.get('income', 0)
    total_expense = stats.get('expense', 0)
    balance = total_income - total_expense

    report = (
        f"🗓 Отчет с {week_ago.strftime('%d.%m')} по {now.strftime('%d.%m')}:\n\n"
        f"🟢 Доходы: {total_income:.2f} ₽\n"
        f"🔴 Расходы: {total_expense:.2f} ₽\n"
        f"⚖️ Баланс: {balance:.2f} ₽\n\n"
        f"📋 Все операции за неделю:\n"
    )

    if transactions:
        for op in transactions:
            op_time = op.date.astimezone(timezone).strftime('%d.%m %H:%M')
            report += f"\n• {op_time} - {'🟢' if op.type == 'income' else '🔴'} {op.amount:.2f} ₽ - {op.description or 'Без описания'} ({op.category or 'Без категории'})"
    else:
        report += "\nНет операций за неделю."

    await callback.message.edit_text(report, reply_markup=report_kb())

@router.callback_query(F.data == "report_by_category")
async def ask_report_category(callback: CallbackQuery):
    await callback.answer()
    categories = await get_categories_for_user(callback.from_user.id)
    if not categories:
        await callback.message.answer("У вас нет сохранённых категорий.", reply_markup=main_kb())
        return

    kb = report_category_kb(categories)
    await callback.message.answer("Выберите категорию для отчёта:", reply_markup=kb)

@router.callback_query(F.data.startswith("rep_cat_"))
async def show_report_by_category(callback: CallbackQuery):
    category = callback.data.replace("rep_cat_", "")
    timezone = pytz.timezone('Europe/Moscow')
    now = datetime.now(timezone)
    week_ago = now - timedelta(days=7)

    transactions = await get_transactions_by_category(callback.from_user.id, category, week_ago)

    if not transactions:
        await callback.message.answer(f"Нет операций в категории '{category}' за неделю.", reply_markup=main_kb())
        return

    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    report = (
        f"🗓 Отчет по категории '{category}' за неделю:\n\n"
        f"🟢 Доходы: {total_income:.2f} ₽\n"
        f"🔴 Расходы: {total_expense:.2f} ₽\n"
        f"⚖️ Баланс: {balance:.2f} ₽\n\n"
        f"Операции:\n"
    )

    for op in transactions:
        op_time = op.date.astimezone(timezone).strftime('%d.%m %H:%M')
        report += f"\n• {op_time} - {'🟢' if op.type == 'income' else '🔴'} {op.amount:.2f} ₽ - {op.description or 'Без описания'}"

    await callback.message.edit_text(report, reply_markup=report_kb())

@router.callback_query(F.data == "delete_data")
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "⚠️ Вы уверены что хотите удалить ВСЕ данные?\n"
        "Это действие нельзя отменить!",
        reply_markup=confirm_delete_kb()
    )
    await state.set_state(DeleteStates.CONFIRM)

@router.callback_query(F.data == "confirm_delete", DeleteStates.CONFIRM)
async def process_delete(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    deleted_count = await delete_user_data(user_id)

    await callback.message.edit_text(
        f"✅ Удалено {deleted_count} записей",
        reply_markup=main_kb()
    )
    await state.clear()

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    name = user.full_name or user.username or "пользователь"
    await callback.message.edit_text(
        f"Привет, {name}! 🤙\n\n"
        "Это ваш персональный финансовый трекер 📊\n"
        "Начните с добавления первой операции:",
        reply_markup=main_kb()
    )

@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    name = user.full_name or user.username or "пользователь"
    await callback.message.edit_text(
        f"Привет, {name}! 🤙\n\n"
        "Это ваш персональный финансовый трекер 📊\n"
        "Начните с добавления первой операции:",
        reply_markup=main_kb()
    )    