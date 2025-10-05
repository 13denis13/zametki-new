import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.handlers.handlers import router
from app.baza.database import init_db, send_weekly_reports
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN обязательна")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))

dp.include_router(router)

async def on_startup(app: web.Application):
    if not WEBHOOK_URL:
        raise ValueError("Переменная окружения WEBHOOK_URL обязательна")
    
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    
    try:
        await bot.set_webhook(webhook_url)
        logger.info(f"Вебхук установлен на: {webhook_url}")
    except Exception as e:
        logger.error(f"Не удалось установить вебхук: {e}")
        raise
    
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
    logger.info("Вебхук бота установлен и планировщик запущен.")

async def on_shutdown(app: web.Application):
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук удален")
    except Exception as e:
        logger.error(f"Ошибка удаления вебхука: {e}")
    
    try:
        if scheduler.running:
            scheduler.shutdown()
        logger.info("Планировщик остановлен")
    except Exception as e:
        logger.error(f"Ошибка остановки планировщика: {e}")
    
    await bot.session.close()
    logger.info("Сессия бота закрыта")

async def handle_webhook(request):
    if request.path != WEBHOOK_PATH or request.method != 'POST':
        return web.Response(text="Не найдено", status=404)
    
    try:
        json_data = await request.json()
        update = Update(**json_data)
        await dp.process_update(update)
        return web.Response(text="OK", status=200)
    except asyncio.CancelledError:
        logger.warning("Запрос был отменен")
        raise
    except Exception as e:
        logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
        return web.Response(text="Внутренняя ошибка сервера", status=500)

def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    
    web.run_app(
        app,
        host=APP_HOST,
        port=APP_PORT
    )

if __name__ == "__main__":
    main()
