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
APP_HOST = os.getenv("APP_HOST", "0.0.0.0") # Убедимся, что хост установлен
APP_PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # Убедимся, что это задано в env

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
        logger.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
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
    logger.info("Bot webhook set and scheduler started.")

async def on_shutdown(app: web.Application):
    try:
        # Удаляем вебхук у Telegram
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted from Telegram")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")

    try:
        if scheduler.running:
            scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

    # Закрываем сессию бота
    await bot.session.close()
    logger.info("Bot session closed")


async def handle_webhook(request):
    if request.path == WEBHOOK_PATH and request.method == 'POST':
        try:
            json_data = await request.json()
            update = Update(**json_data)
            await dp.process_update(update)
            return web.Response(text="OK", status=200)
        except asyncio.CancelledError:
            logger.warning("Request was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
            return web.Response(text="Internal Server Error", status=500)
    else:
        # Этот else теперь не нужен, так как мы добавим отдельный маршрут для /
        # Но если оставить, он будет возвращать 404 для всех, кроме /webhook
        return web.Response(text="Not Found", status=404)

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ КОРНЕВОГО ПУТИ ---
async def handle_root(request):
    """Простой обработчик для корневого пути, возвращающий OK."""
    return web.Response(text="Bot is running!", status=200)
# --- КОНЕЦ НОВОЙ ФУНКЦИИ ---

def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Добавляем маршрут для вебхука
    app.router.add_post(WEBHOOK_PATH, handle_webhook)

    # --- ДОБАВЛЯЕМ МАРШРУТ ДЛЯ КОРНЕВОГО ПУТИ ---
    app.router.add_get('/', handle_root)
    # --- КОНЕЦ ДОБАВЛЕНИЯ ---

    web.run_app(
        app,
        host=APP_HOST,
        port=APP_PORT
    )

if __name__ == "__main__":
    main()
