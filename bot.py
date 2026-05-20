import os
import json
import logging
from datetime import datetime, time
import pytz

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# --- Настройки ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
JOURNAL_FILE = "journal.json"
TIMEZONE = pytz.timezone("Asia/Bangkok")  # Самуи — Bangkok UTC+7

# Вопросы для рефлексии
QUESTIONS = [
    "🌙 Как прошёл сегодняшний день? Что запомнилось больше всего?",
    "🙏 Кому или чему ты сегодня благодарен?",
    "📖 Какой урок или вывод можно вынести из сегодняшнего дня?",
    "🗓 Какой у тебя план на завтра? Три главных дела.",
]

# Состояния диалога
Q1, Q2, Q3, Q4 = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Работа с журналом ---

def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return {}
    with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_entry(date_str: str, answers: dict):
    journal = load_journal()
    journal[date_str] = {
        "date": date_str,
        "saved_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        "answers": answers,
    }
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)


# --- Хендлеры команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "Привет! Я твой бот для ежевечерней рефлексии 🌙\n\n"
        "Каждый вечер в 21:00 я буду присылать тебе вопросы.\n\n"
        "Команды:\n"
        "/ask — задать вопросы прямо сейчас\n"
        "/history — последние 7 записей\n"
        "/cancel — отменить текущий диалог"
    )


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    context.user_data["answers"] = {}
    context.user_data["date"] = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    await update.message.reply_text(
        "Время для вечерней рефлексии ✍️\n\n" + QUESTIONS[0]
    )
    return Q1


async def answer_q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["day"] = update.message.text
    await update.message.reply_text(QUESTIONS[1])
    return Q2


async def answer_q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["gratitude"] = update.message.text
    await update.message.reply_text(QUESTIONS[2])
    return Q3


async def answer_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["lesson"] = update.message.text
    await update.message.reply_text(QUESTIONS[3])
    return Q4


async def answer_q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["plan"] = update.message.text
    date_str = context.user_data["date"]
    save_entry(date_str, context.user_data["answers"])
    await update.message.reply_text(
        "✅ Всё записано. Хорошего вечера!\n\n"
        f"Запись за {date_str} сохранена в дневник."
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Напиши /ask чтобы начать снова.")
    return ConversationHandler.END


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    journal = load_journal()
    if not journal:
        await update.message.reply_text("Дневник пока пустой. Напиши /ask чтобы начать.")
        return

    sorted_entries = sorted(journal.items(), reverse=True)[:7]
    text = "📔 *Последние записи:*\n\n"

    for date_str, entry in sorted_entries:
        answers = entry.get("answers", {})
        text += f"*{date_str}*\n"
        text += f"🌙 {answers.get('day', '—')}\n"
        text += f"🙏 {answers.get('gratitude', '—')}\n"
        text += f"📖 {answers.get('lesson', '—')}\n"
        text += f"🗓 {answers.get('plan', '—')}\n"
        text += "─────────────\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# --- Ежевечерняя рассылка ---

async def evening_questions(context: ContextTypes.DEFAULT_TYPE):
    """Запускается каждый день в 21:00 по Bangkok."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="Добрый вечер! Время для рефлексии 🌙\n\nНапиши /ask чтобы начать.",
    )


# --- Главная функция ---

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Диалог из 4 вопросов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q2)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q4)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("history", history))

    # Планировщик: каждый день в 21:00 Bangkok time
    app.job_queue.run_daily(
        evening_questions,
        time=time(hour=21, minute=0, second=0, tzinfo=TIMEZONE),
    )

    logger.info("Бот запущен.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
