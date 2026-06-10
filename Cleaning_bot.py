import os
import logging
import asyncio
import random
from datetime import datetime, time as dtime
import pytz

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TIMEZONE = pytz.timezone("Asia/Bangkok")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

CLEANING_BOT_TOKEN = os.environ.get("CLEANING_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))


async def floors_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Суббота — помыть полы."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="🧹 *Уборка: полы*\n\nСегодня моем полы — свежесть в доме того стоит ✨",
        parse_mode="Markdown",
    )


async def dust_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Среда — протереть пыль."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="🪮 *Уборка: пыль*\n\nПройдись по полкам и поверхностям — убери пыль 🌬",
        parse_mode="Markdown",
    )


async def bathroom_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Воскресенье — раковина и унитаз."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="🚿 *Уборка: санузел*\n\nПомой раковину и унитаз — чистота и порядок 🧼",
        parse_mode="Markdown",
    )


async def windows_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Раз в 2 месяца (1-го числа нечётного месяца) — помыть окна."""
    month = datetime.now(TIMEZONE).month
    if month % 2 == 1:  # январь, март, май... — раз в два месяца
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text="🪟 *Уборка: окна*\n\nПора помыть окна — больше света в доме ☀️",
            parse_mode="Markdown",
        )


# =====================
# ХЕНДЛЕРЫ
# =====================

async def cleaning_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "🧽 *Бот уборки квартиры*\n\n"
        "Расписание напоминаний:\n"
        "• 🧹 Полы — воскресенье\n"
        "• 🚿 Раковина и унитаз — воскресенье\n"
        "• 🪮 Пыль — понедельник\n"
        "• 🪟 Окна — раз в 2 месяца\n\n"
        "Все напоминания в 12:00",
        parse_mode="Markdown",
    )


# =====================
# ЗАПУСК
# =====================

async def main() -> list:
    app = Application.builder().token(CLEANING_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cleaning_start))

    # Полы и санузел — воскресенье (6), пыль — понедельник (0); все в 12:00
    app.job_queue.run_daily(floors_reminder, time=dtime(hour=12, minute=0, tzinfo=TIMEZONE), days=(6,))
    app.job_queue.run_daily(bathroom_reminder, time=dtime(hour=12, minute=0, tzinfo=TIMEZONE), days=(6,))
    app.job_queue.run_daily(dust_reminder, time=dtime(hour=12, minute=0, tzinfo=TIMEZONE), days=(0,))
    # Окна — 1-го числа, только в нечётные месяцы (раз в 2 месяца)
    app.job_queue.run_monthly(windows_reminder, when=dtime(hour=12, minute=0, tzinfo=TIMEZONE), day=1)

    return [app]


async def _run_standalone():
    apps = await main()
    app = apps[0]
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("🧽 Бот уборки запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_run_standalone())
