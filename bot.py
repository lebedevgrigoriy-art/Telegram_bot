import os
import json
import logging
import time
import hmac
import hashlib
import requests
from datetime import datetime, time as dtime
from collections import Counter
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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
BYBIT_BOT_TOKEN = os.environ.get("BYBIT_BOT_TOKEN")
BYBIT_CHAT_ID = int(os.environ.get("BYBIT_CHAT_ID"))
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")

JOURNAL_FILE = "journal.json"
SNAPSHOT_FILE = "snapshot.json"

Q1, Q2, Q3, Q4, Q5 = range(5)

QUESTIONS = [
    "🌙 Как прошёл сегодняшний день? Что запомнилось больше всего?",
    "🙏 Кому или чему ты сегодня благодарен?",
    "📖 Какой урок или вывод можно вынести из сегодняшнего дня?",
    "🗓 Какой у тебя план на завтра? Три главных дела.",
]


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


def get_yesterday_plan():
    """Возвращает план на сегодня из вчерашней записи."""
    journal = load_journal()
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    sorted_dates = sorted(journal.keys(), reverse=True)
    for date_str in sorted_dates:
        if date_str < today:
            plan = journal[date_str].get("answers", {}).get("plan", "")
            if plan:
                return date_str, plan
    return None, None


def get_monthly_gratitude_summary():
    """Собирает тезисы благодарности за последний месяц."""
    journal = load_journal()
    now = datetime.now(TIMEZONE)
    current_month = now.strftime("%Y-%m")

    gratitudes = []
    for date_str, entry in journal.items():
        if date_str.startswith(current_month):
            g = entry.get("answers", {}).get("gratitude", "")
            if g:
                gratitudes.append(g)

    return gratitudes


async def start_reflection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "Привет! Я твой бот для ежевечерней рефлексии 🌙\n\n"
        "Каждый вечер в 21:00 я буду присылать тебе вопросы.\n\n"
        "Команды:\n"
        "/ask — начать рефлексию прямо сейчас\n"
        "/history — последние 7 записей\n"
        "/gratitude — сводка благодарностей за месяц\n"
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

    # После плана показываем вчерашний план и спрашиваем про выполнение
    date_str, yesterday_plan = get_yesterday_plan()
    if yesterday_plan:
        await update.message.reply_text(
            f"📋 *Твой план со вчера ({date_str}):*\n\n{yesterday_plan}\n\n"
            f"✅ Удалось выполнить что-то из списка? Напиши коротко.",
            parse_mode="Markdown"
        )
        return Q5

    # Если вчерашнего плана нет — завершаем
    date_str = context.user_data["date"]
    save_entry(date_str, context.user_data["answers"])
    await update.message.reply_text(
        f"✅ Всё записано. Хорошего вечера!\n\nЗапись за {date_str} сохранена."
    )
    return ConversationHandler.END


async def answer_plan_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["plan_review"] = update.message.text
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
        if answers.get("plan_review"):
            text += f"✅ {answers.get('plan_review')}\n"
        text += f"🌙 {answers.get('day', '—')}\n"
        text += f"🙏 {answers.get('gratitude', '—')}\n"
        text += f"📖 {answers.get('lesson', '—')}\n"
        text += f"🗓 {answers.get('plan', '—')}\n"
        text += "─────────────\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def gratitude_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает тезисную сводку благодарностей за месяц через Claude API."""
    if update.effective_chat.id != MY_CHAT_ID:
        return

    gratitudes = get_monthly_gratitude_summary()
    now = datetime.now(TIMEZONE)

    if not gratitudes:
        await update.message.reply_text("За этот месяц записей ещё нет.")
        return

    await update.message.reply_text("Анализирую благодарности за месяц... ⏳")

    # Формируем текст для анализа
    all_gratitudes = "\n".join(f"- {g}" for g in gratitudes)
    month_name = now.strftime("%B %Y")

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": f"""Вот записи благодарности человека за {month_name}:

{all_gratitudes}

Сделай тезисную сводку на русском языке:
1. Кому или чему он благодарил чаще всего (имена, явления, вещи)
2. За что именно — коротко и по существу
3. Общий тон благодарностей

Пиши коротко, без воды, 5-8 предложений максимум."""
                }]
            },
            timeout=30,
        )
        data = response.json()
        summary = data["content"][0]["text"]
    except Exception as e:
        # Если API недоступен — делаем простую сводку сами
        summary = f"За {month_name} записано {len(gratitudes)} дней благодарности.\n\n"
        summary += "Записи:\n" + "\n".join(f"• {g[:100]}" for g in gratitudes[-5:])

    await update.message.reply_text(
        f"🙏 *Благодарности за {month_name}*\n\n{summary}",
        parse_mode="Markdown"
    )


async def evening_questions(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="Добрый вечер! Время для рефлексии 🌙\n\nНапиши /ask чтобы начать.",
    )


async def monthly_gratitude_report(context: ContextTypes.DEFAULT_TYPE):
    """Автоматический отчёт в первый день месяца."""
    gratitudes = get_monthly_gratitude_summary()
    now = datetime.now(TIMEZONE)
    month_name = now.strftime("%B %Y")

    if not gratitudes:
        return

    all_gratitudes = "\n".join(f"- {g}" for g in gratitudes)

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": f"""Вот записи благодарности человека за {month_name}:

{all_gratitudes}

Сделай тезисную сводку на русском языке:
1. Кому или чему он благодарил чаще всего
2. За что именно — коротко и по существу
3. Общий тон благодарностей

Пиши коротко, без воды, 5-8 предложений максимум."""
                }]
            },
            timeout=30,
        )
        data = response.json()
        summary = data["content"][0]["text"]
    except Exception:
        summary = "\n".join(f"• {g[:100]}" for g in gratitudes[-5:])

    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text=f"🙏 *Итоги благодарностей за {month_name}*\n\n{summary}",
        parse_mode="Markdown",
    )


# =====================
# BYBIT ТРЕКЕР
# =====================

def bybit_request(endpoint, params=None):
    if params is None:
        params = {}
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
    r = requests.get(
        f"https://api.bybit.com{endpoint}",
        headers=headers,
        params=params,
        timeout=10,
    )
    return r.json()


async def bybit_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != BYBIT_CHAT_ID:
        return
    await update.message.reply_text(
        "Bybit трекер пока недоступен — API не предоставляет доступ к балансу Trading Bot аккаунта."
    )


# =====================
# ЗАПУСК
# =====================

async def main():
    reflection_app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask)],
        states={
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_plan_review)],
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
    reflection_app.add_handler(CommandHandler("gratitude", gratitude_summary))

    reflection_app.job_queue.run_daily(
        evening_questions,
        time=dtime(hour=21, minute=0, second=0, tzinfo=TIMEZONE),
    )

    # Первого числа каждого месяца в 09:00
    reflection_app.job_queue.run_monthly(
        monthly_gratitude_report,
        when=dtime(hour=9, minute=0, second=0, tzinfo=TIMEZONE),
        day=1,
    )

    bybit_app = Application.builder().token(BYBIT_BOT_TOKEN).build()
    bybit_app.add_handler(CommandHandler("status", bybit_status))

    async with reflection_app, bybit_app:
        await reflection_app.start()
        await bybit_app.start()
        await reflection_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await bybit_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Оба бота запущены.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
