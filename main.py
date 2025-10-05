import asyncio
from asyncio.log import logger
import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.handlers.handlers import router
from app.baza.database import init_db, send_weekly_reports
import pytz

load_dotenv()

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    
    dp.include_router(router)
    await init_db()

    scheduler.add_job(
        send_weekly_reports,
        'cron',
        day_of_week='mon',
        hour=9,
        minute=0,
        kwargs={'bot': bot}
    )
    scheduler.start()

   
    
    try:
        logger.info("Starting bot")
        await dp.start_polling(bot)
    finally:
        logger.info("Stopping bot")
        scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
    