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

# Получаем токен и URL для вебхука
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("PORT", 10000))

# Инициализируем бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))

# Подключаем роутер
dp.include_router(router)

# Устанавливаем вебхук при старте
async def on_startup(app: web.Application):
    webhook_url = f"https://<zametki-new
>.onrender.com{WEBHOOK_PATH}"  
    await bot.set_webhook(webhook_url)
    await init_db()

    # Добавляем задачу в планировщик
    scheduler.add_job(
        send_weekly_reports,
        'cron',
        day_of_week='mon',
        hour=9,
        minute=0,
        kwargs={'bot': bot}
    )
    scheduler.start()
    logger.info("Bot webhook set and scheduler started.")

# Удаляем вебхук при выключении
async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    scheduler.shutdown()
    logger.info("Bot webhook deleted and scheduler stopped.")

# Обработчик вебхука
async def handle_webhook(request):
    if request.path == WEBHOOK_PATH and request.method == 'POST':
        try:
            json_data = await request.json()
            update = Update(**json_data)
            await dp.process_update(update)
            return web.Response(text="OK", status=200)
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return web.Response(text="Error", status=500)
    else:
        return web.Response(text="Not Found", status=404)

def main():
    # Создаём aiohttp приложение
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_post(WEBHOOK_PATH, handle_webhook)

    # Запускаем приложение
    web.run_app(
        app,
        host=APP_HOST,
        port=APP_PORT
    )

if __name__ == "__main__":
    main()
