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

PLANT_BOT_TOKEN = os.environ.get("PLANT_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))

WATERING_MESSAGES = [
    "🌿 *Время полить цветы!*\n\nТвои зелёные друзья ждут водички 💧",
    "🪴 *Полив!*\n\nДай растениям попить — они отблагодарят тебя свежей зеленью 🌱",
    "💧 *Пора поливать цветы*\n\nНемного воды — и они снова счастливы 🌿",
    "🌸 *Цветы хотят пить!*\n\nУдели им пару минут — полей как следует 💦",
]


async def water_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Понедельник и пятница 09:00 — полить цветы."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text=random.choice(WATERING_MESSAGES),
        parse_mode="Markdown",
    )


async def settle_water_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Вторник и пятница 09:00 — поставить воду отстаиваться (за 3 дня до полива пт и пн)."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text=(
            "🚰 *Поставь воду отстаиваться*\n\n"
            "Набери воду для полива — пусть постоит минимум 3 дня, "
            "чтобы хлор выветрился и вода стала мягче для растений 💧"
        ),
        parse_mode="Markdown",
    )


async def loosen_soil_reminder(context: ContextTypes.DEFAULT_TYPE):
    """1-го числа месяца 09:00 — разрыхлить почву."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text=(
            "🌱 *Пора разрыхлить почву*\n\n"
            "Аккуратно разрыхли верхний слой земли в горшках — это поможет корням дышать. "
            "Рыхли неглубоко и осторожно, чтобы *не повредить корни* 🤲"
        ),
        parse_mode="Markdown",
    )


# =====================
# ХЕНДЛЕРЫ
# =====================

async def plant_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "🪴 *Бот ухода за цветами*\n\n"
        "Я напомню:\n"
        "• 💧 Полить — пн и пт в 09:00\n"
        "• 🚰 Отстоять воду — вт и пт (за 3 дня до полива)\n"
        "• 🌱 Разрыхлить почву — 1-го числа месяца\n\n"
        "/water — напомнить полить сейчас",
        parse_mode="Markdown",
    )


async def water_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(random.choice(WATERING_MESSAGES), parse_mode="Markdown")


# =====================
# ЗАПУСК
# =====================

async def main() -> list:
    app = Application.builder().token(PLANT_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", plant_start))
    app.add_handler(CommandHandler("water", water_command))

    # Полив: понедельник (0) и пятница (4) в 09:00
    app.job_queue.run_daily(water_reminder, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE), days=(0, 4))
    # Отстаивание воды: вторник (1) и пятница (4) — за 3 дня до пятницы и понедельника
    app.job_queue.run_daily(settle_water_reminder, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE), days=(1, 4))
    # Рыхление: 1-го числа каждого месяца в 09:00
    app.job_queue.run_monthly(loosen_soil_reminder, when=dtime(hour=9, minute=0, tzinfo=TIMEZONE), day=1)

    return [app]


async def _run_standalone():
    apps = await main()
    app = apps[0]
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("🪴 Бот полива запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_run_standalone())
