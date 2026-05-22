import os
import json
import logging
from datetime import datetime, time as dtime
import pytz
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from pybit.unified_trading import HTTP

TIMEZONE = pytz.timezone("Asia/Bangkok")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
BYBIT_BOT_TOKEN = os.environ.get("BYBIT_BOT_TOKEN")
BYBIT_CHAT_ID = int(os.environ.get("BYBIT_CHAT_ID"))
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")
BYBIT_BOT_ID = os.environ.get("BYBIT_BOT_ID")

bybit_session = HTTP(
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
)

Q1, Q2, Q3, Q4 = range(4)

QUESTIONS = [
    "🌙 Как прошёл сегодняшний день? Что запомнилось больше всего?",
    "🙏 Кому или чему ты сегодня благодарен?",
    "📖 Какой урок или вывод можно вынести из сегодняшнего дня?",
    "🗓 Какой у тебя план на завтра? Три главных дела.",
]

JOURNAL_FILE = "journal.json"


# =====================
# ЖУРНАЛ РЕФЛЕКСИИ
# =====================

def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return {}
    with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_entry(date_str, answers):
    journal = load_journal()
    journal[date_str] = {
        "date": date_str,
        "saved_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        "answers": answers,
    }
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)


async def start_reflection(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("Время для вечерней рефлексии ✍️\n\n" + QUESTIONS[0])
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
        f"✅ Всё записано. Хорошего вечера!\n\nЗапись за {date_str} сохранена."
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


async def evening_questions(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="Добрый вечер! Время для рефлексии 🌙\n\nНапиши /ask чтобы начать.",
    )


# =====================
# BYBIT ТРЕКЕР
# =====================

def get_grid_pnl():
    try:
        response = bybit_session.get_spot_algo_orders(
            orderFilter="StopOrder",
            botId=BYBIT_BOT_ID,
        )
        return response
    except Exception as e:
        return {"error": str(e)}


def format_bybit_report(data):
    try:
        if "error" in data:
            return f"❌ Ошибка запроса: {data['error']}"

        ret_code = data.get("retCode", -1)
        ret_msg = data.get("retMsg", "")

        if ret_code != 0:
            return (
                f"⚠️ Bybit ответил с ошибкой:\n"
                f"Код: `{ret_code}`\n"
                f"Сообщение: `{ret_msg}`\n\n"
                f"Сырой ответ:\n`{json.dumps(data)[:500]}`"
            )

        result = data.get("result", {})
        now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")

        return (
            f"📊 *Данные грид-бота BTC/USDT*\n"
            f"_{now}_\n\n"
            f"`{json.dumps(result, indent=2)[:800]}`"
        )
    except Exception as e:
        return f"❌ Ошибка: {e}\n\nСырой ответ:\n`{json.dumps(data)[:500]}`"


async def bybit_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != BYBIT_CHAT_ID:
        return
    await update.message.reply_text("Запрашиваю данные с Bybit... ⏳")
    data = get_grid_pnl()
    text = format_bybit_report(data)
    await update.message.reply_text(text, parse_mode="Markdown")


async def weekly_bybit_report(context: ContextTypes.DEFAULT_TYPE):
    data = get_grid_pnl()
    text = "🗓 *Еженедельный отчёт Bybit*\n\n" + format_bybit_report(data)
    await context.bot.send_message(
        chat_id=BYBIT_CHAT_ID,
        text=text,
        parse_mode="Markdown",
    )


# =====================
# ЗАПУСК
# =====================

async def main():
    reflection_app = Application.builder().token(BOT_TOKEN).build()

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

    reflection_app.add_handler(CommandHandler("start", start_reflection))
    reflection_app.add_handler(conv_handler)
    reflection_app.add_handler(CommandHandler("history", history))
    reflection_app.job_queue.run_daily(
        evening_questions,
        time=dtime(hour=21, minute=0, second=0, tzinfo=TIMEZONE),
    )

    bybit_app = Application.builder().token(BYBIT_BOT_TOKEN).build()
    bybit_app.add_handler(CommandHandler("status", bybit_status))
    bybit_app.job_queue.run_daily(
        weekly_bybit_report,
        time=dtime(hour=20, minute=0, second=0, tzinfo=TIMEZONE),
        days=(6,),
    )

    async with reflection_app, bybit_app:
        await reflection_app.start()
        await bybit_app.start()
        await reflection_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await bybit_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Оба бота запущены.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
