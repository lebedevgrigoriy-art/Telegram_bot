import os
import json
import logging
from datetime import datetime, timedelta, time as dtime
import pytz
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

TIMEZONE = pytz.timezone("Asia/Bangkok")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("VISA_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))

VISA_FILE = "visa.json"

ENTER_DATE, ENTER_DAYS = range(2)


def load_visa():
    if not os.path.exists(VISA_FILE):
        return None
    with open(VISA_FILE, "r") as f:
        return json.load(f)


def save_visa(entry_date, days):
    data = {
        "entry_date": entry_date,
        "days": days,
        "expiry_date": (datetime.strptime(entry_date, "%d.%m.%Y") + timedelta(days=days)).strftime("%d.%m.%Y"),
    }
    with open(VISA_FILE, "w") as f:
        json.dump(data, f)
    return data


def days_left(expiry_date_str):
    expiry = datetime.strptime(expiry_date_str, "%d.%m.%Y")
    today = datetime.now(TIMEZONE).replace(tzinfo=None)
    return (expiry - today).days


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    visa = load_visa()
    text = (
        "🇹🇭 *Визовый будильник*\n\n"
        "Команды:\n"
        "/set — задать дату въезда и срок визы\n"
        "/status — сколько дней осталось\n"
        "/cancel — отменить ввод\n"
    )
    if visa:
        left = days_left(visa["expiry_date"])
        text += f"\n📅 Текущая виза истекает: *{visa['expiry_date']}*\nОсталось: *{left} дн.*"
    await update.message.reply_text(text, parse_mode="Markdown")


async def set_visa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "📅 Введи дату въезда в формате ДД.ММ.ГГГГ\nНапример: `15.05.2026`",
        parse_mode="Markdown"
    )
    return ENTER_DATE


async def enter_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["entry_date"] = text
        await update.message.reply_text(
            "✅ Дата принята.\n\nТеперь введи количество дней разрешённого пребывания.\nНапример: `30` или `60`",
            parse_mode="Markdown"
        )
        return ENTER_DAYS
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введи дату в формате ДД.ММ.ГГГГ")
        return ENTER_DATE


async def enter_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        days = int(text)
        if days <= 0 or days > 365:
            raise ValueError
        entry_date = context.user_data["entry_date"]
        visa = save_visa(entry_date, days)
        left = days_left(visa["expiry_date"])
        await update.message.reply_text(
            f"✅ *Виза сохранена!*\n\n"
            f"📅 Въезд: {entry_date}\n"
            f"⏳ Срок: {days} дней\n"
            f"🔴 Истекает: *{visa['expiry_date']}*\n"
            f"📊 Осталось: *{left} дн.*\n\n"
            f"Буду напоминать за 14, 7, 3 и 1 день до окончания.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введи целое число от 1 до 365")
        return ENTER_DAYS


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    visa = load_visa()
    if not visa:
        await update.message.reply_text("Виза не задана. Используй /set")
        return

    left = days_left(visa["expiry_date"])

    if left < 0:
        emoji = "🚨"
        status_text = f"ПРОСРОЧЕНА на {abs(left)} дней!"
    elif left == 0:
        emoji = "🚨"
        status_text = "истекает СЕГОДНЯ!"
    elif left <= 3:
        emoji = "🔴"
        status_text = f"осталось *{left} дн.* — срочно!"
    elif left <= 7:
        emoji = "🟠"
        status_text = f"осталось *{left} дн.*"
    elif left <= 14:
        emoji = "🟡"
        status_text = f"осталось *{left} дн.*"
    else:
        emoji = "🟢"
        status_text = f"осталось *{left} дн.*"

    # Прогресс-бар
    total = visa["days"]
    used = total - left
    pct = max(0, min(100, int(used / total * 100)))
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)

    await update.message.reply_text(
        f"{emoji} *Статус визы*\n\n"
        f"📅 Въезд: {visa['entry_date']}\n"
        f"🔴 Истекает: {visa['expiry_date']}\n"
        f"⏳ {status_text}\n\n"
        f"`[{bar}]` {pct}% использовано",
        parse_mode="Markdown"
    )


async def check_visa_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная проверка визы и отправка напоминаний."""
    visa = load_visa()
    if not visa:
        return

    left = days_left(visa["expiry_date"])

    if left in [14, 7, 3, 1]:
        if left == 1:
            msg = f"🚨 *Завтра истекает виза!*\n\nОстался *1 день*. Срочно планируй бордер ран или продление!"
        elif left == 3:
            msg = f"🔴 *Виза истекает через 3 дня!*\n\nПора планировать бордер ран!"
        elif left == 7:
            msg = f"🟠 *Эй, пора планировать бордер ран!*\n\nДо конца визы осталось *7 дней*."
        else:
            msg = f"🟡 *Напоминание о визе*\n\nДо конца визы осталось *14 дней*. Начинай думать о продлении."

        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=msg + f"\n\n📅 Истекает: {visa['expiry_date']}",
            parse_mode="Markdown"
        )
    elif left < 0:
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=f"🚨 *ВИЗА ПРОСРОЧЕНА!*\n\nПросрочка: {abs(left)} дней.\nНемедленно займись легализацией!",
            parse_mode="Markdown"
        )


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set", set_visa)],
        states={
            ENTER_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_date)],
            ENTER_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(conv_handler)

    # Проверка каждый день в 10:00
    app.job_queue.run_daily(
        check_visa_reminders,
        time=dtime(hour=10, minute=0, tzinfo=TIMEZONE),
    )

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Визовый бот запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
