import os
import logging
import requests
import asyncio
from datetime import datetime, time as dtime
import pytz

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TIMEZONE = pytz.timezone("Asia/Bangkok")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

QUOTE_BOT_TOKEN = os.environ.get("QUOTE_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


# =====================
# GEMINI
# =====================

def ask_gemini(prompt: str, max_tokens: int = 500) -> str:
    """Запрос к Gemini с повтором при пустом ответе. Пустая строка если ключа нет или 2 неудачи."""
    if not GEMINI_API_KEY:
        return ""
    for attempt in range(2):
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": 0.9,
                        "thinkingConfig": {"thinkingBudget": 0},
                    },
                },
                timeout=30,
            )
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        return text
            logger.error(f"Gemini empty (attempt {attempt + 1}): {str(data)[:300]}")
        except Exception as e:
            logger.error(f"Gemini error (attempt {attempt + 1}): {e}")
    return ""


# =====================
# SUPABASE — контекст рефлексии
# =====================

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def get_recent_reflections(limit=3) -> list:
    """Последние 3 записи для контекста — даёт глубину, но не слишком много старого."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/journal",
            headers=sb_headers(),
            params={"order": "date.desc", "limit": str(limit)},
            timeout=10,
        )
        return resp.json() if resp.ok else []
    except Exception as e:
        logger.error(f"get_reflections error: {e}")
        return []


def build_context() -> str:
    """Контекст из 3 последних записей, с явной пометкой свежести каждой."""
    rows = get_recent_reflections()
    if not rows:
        logger.warning("Цитата: записей в journal не найдено — контекст пустой")
        return ""
    pieces = []
    for i, r in enumerate(rows):
        bits = []
        if r.get("day_text"):
            bits.append(f"день: {r['day_text']}")
        if r.get("mood"):
            bits.append(f"состояние: {r['mood']}")
        if r.get("lesson"):
            bits.append(f"урок: {r['lesson']}")
        if r.get("gratitude"):
            bits.append(f"благодарность: {r['gratitude']}")
        if r.get("self_gratitude"):
            bits.append(f"гордость: {r['self_gratitude']}")
        if bits:
            tag = "СЕГОДНЯ/последняя" if i == 0 else f"{i+1}-я по свежести (раньше)"
            pieces.append(f"[{tag}, {r.get('date','')}]: " + "; ".join(bits))
    context = "\n".join(pieces)
    logger.info(f"Цитата: контекст из {len(pieces)} записей, {len(context)} симв.")
    return context


# =====================
# ЦИТАТА
# =====================

def generate_quote() -> str:
    context = build_context()
    if context:
        prompt = (
            "Ты — мудрый наставник, который ведёт с человеком утренний диалог. "
            "Вот его последние 3 записи из дневника саморефлексии, от самой свежей к более старым:\n\n"
            f"{context}\n\n"
            "ПРАВИЛО ПРИОРИТЕТА ТЕМ: если тема/проблема из старых записей (2-я, 3-я по свежести) "
            "НЕ упоминается в самой свежей записи — значит человек с ней уже разобрался или сдвинулся "
            "дальше, и ты НЕ должен её поднимать. Бери тему из самой свежей записи как главную. "
            "Старые записи используй только чтобы лучше понять характер и контекст человека в целом "
            "(например, какие темы ему важны, как он пишет), а не чтобы тащить конкретную прошлую тему, "
            "которой уже нет в свежей записи.\n\n"
            "Сделай так:\n"
            "1) В 1-2 предложениях мягко отметь, что ты увидел именно в САМОЙ СВЕЖЕЙ записи — "
            "обращайся на «ты», тепло и по-человечески.\n"
            "2) Подбери ОДНУ подлинную цитату известного человека (философа, писателя, учёного, "
            "предпринимателя), которая прямо перекликается именно с этим. Не выдумывай цитату.\n\n"
            "Формат ответа:\n"
            "<твоё короткое наблюдение>\n\n«Цитата»\n— Автор"
        )
    else:
        prompt = (
            "Подбери ОДНУ реальную, проверяемую вдохновляющую цитату известного человека "
            "(философа, писателя, учёного, предпринимателя) о развитии, дисциплине или смысле. "
            "Цитата должна быть подлинной, не выдумывай. "
            "Ответь СТРОГО в формате:\n«Цитата»\n— Автор\n\nБез пояснений."
        )
    quote = ask_gemini(prompt, max_tokens=800)
    return quote


async def send_quote(bot, chat_id):
    quote = generate_quote()
    if not quote:
        await bot.send_message(
            chat_id=chat_id,
            text="🌅 Доброе утро! (Цитата заработает после добавления GEMINI_API_KEY.)",
        )
        return
    await bot.send_message(
        chat_id=chat_id,
        text=f"🌅 *Доброе утро!*\n\n{quote}",
        parse_mode="Markdown",
    )


# =====================
# ХЕНДЛЕРЫ
# =====================

async def quote_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "📜 *Цитата дня*\n\n"
        "Каждое утро в 09:00 — цитата, подобранная под то, о чём ты пишешь в рефлексии.\n\n"
        "/quote — получить цитату прямо сейчас",
        parse_mode="Markdown",
    )


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await send_quote(context.bot, MY_CHAT_ID)


# =====================
# ПЛАНИРОВЩИК
# =====================

async def morning_quote(context: ContextTypes.DEFAULT_TYPE):
    await send_quote(context.bot, MY_CHAT_ID)


# =====================
# ЗАПУСК
# =====================

async def main() -> list:
    app = Application.builder().token(QUOTE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", quote_start))
    app.add_handler(CommandHandler("quote", quote_command))
    app.job_queue.run_daily(morning_quote, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE))
    return [app]


async def _run_standalone():
    apps = await main()
    app = apps[0]
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("📜 Бот цитат запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_run_standalone())
