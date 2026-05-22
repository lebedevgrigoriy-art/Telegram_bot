import os
import time
import hmac
import hashlib
import json
import logging
import requests
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

TIMEZONE = pytz.timezone("Asia/Bangkok")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Токены и ID
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
BYBIT_BOT_TOKEN = os.environ.get("BYBIT_BOT_TOKEN")
BYBIT_CHAT_ID = int(os.environ.get("BYBIT_CHAT_ID"))
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")
BYBIT_BOT_ID = os.environ.get("BYBIT_BOT_ID")

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

def bybit_request(endpoint, params=None):
    if params is None:
        params = {}
    base_url = "https://api.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    params_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_str = timestamp + BYBIT_API_KEY + recv_window + params_str
    signature = hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": recv_window,
    }
    response = requests.get(f"{base_url}{endpoint}", headers=headers, params=params)
    return response.json()


def get_grid_pnl():
    params = {"botId": BYBIT_BOT_ID, "category": "spot"}
    return bybit_request("/v5/spot-algo/get-bot-detail", params)


def format_bybit_report(data):
    try:
        result = data.get("result", {})
        pnl = result.get("pnl", "—")
        pnl_ratio = result.get("pnlRatio", "—")
        grid_profit = result.get("gridProfit", "—")
        invested = result.get("investment", "—")
        capital = result.get("assets", "—")
        pair = result.get("symbol", "BTC/USDT")

        if pnl_ratio != "—":
            pnl_pct = float(pnl_ratio) * 100
            pnl_str = f"{pnl_pct:+.2f}%"
            emoji = "📈" if pnl_pct >= 0 else "📉"
        else:
            pnl_str = "—"
            emoji = "📊"

        now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")
        return (
            f"{emoji} *Грид-бот {pair}*\n"
            f"_{now}_\n\n"
            f"💰 Инвестировано: `{invested} USDT`\n"
            f"📊 P&L: `{pnl} USDT` ({pnl_str})\n"
            f"⚡️ Grid-прибыль: `{grid_profit} USDT`\n"
            f"🏦 Капитал: `{capital} USDT`\n"
        )
    except Exception as e:
        return f"❌ Ошибка: {e}\n\n```{json.dumps(data, indent=2)[:500]}```"


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
    # Бот рефлексии
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

    # Bybit бот
    bybit_app = Application.builder().token(BYBIT_BOT_TOKEN).build()
    bybit_app.add_handler(CommandHandler("status", bybit_status))
    bybit_app.job_queue.run_daily(
        weekly_bybit_report,
        time=dtime(hour=20, minute=0, second=0, tzinfo=TIMEZONE),
        days=(6,),
    )

    # Запускаем оба бота одновременно
    async with reflection_app, bybit_app:
        await reflection_app.start()
        await bybit_app.start()

        await reflection_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await bybit_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        logger.info("Оба бота запущены.")

        # Держим процесс живым
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
