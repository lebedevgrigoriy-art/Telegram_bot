import os
import json
import logging
import requests
import random
from datetime import datetime, timedelta, time as dtime
import pytz
import asyncio
# Supabase через REST API

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

# Токены ботов
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
BYBIT_BOT_TOKEN = os.environ.get("BYBIT_BOT_TOKEN")
BYBIT_CHAT_ID = int(os.environ.get("BYBIT_CHAT_ID"))
CINEMA_BOT_TOKEN = os.environ.get("CINEMA_BOT_TOKEN")
VISA_BOT_TOKEN = os.environ.get("VISA_BOT_TOKEN")
TODOIST_BOT_TOKEN = os.environ.get("TODOIST_BOT_TOKEN")
TODOIST_TOKEN = os.environ.get("TODOIST_TOKEN")
SAVINGS_BOT_TOKEN = os.environ.get("SAVINGS_BOT_TOKEN")
BOOKS_BOT_TOKEN = os.environ.get("BOOKS_BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")
KP_API_KEY = os.environ.get("KP_API_KEY")

SAVINGS_GOAL = 10000
TODOIST_API = "https://api.todoist.com/api/v1"

Q1, Q2, Q_SELF, Q3, Q4, Q5 = range(6)
ENTER_DATE, ENTER_EXPIRY = range(2)
WQ1, WQ2, WQ3, WQ4, WQ5, WQ6, WQ7 = range(10, 17)

QUESTIONS = [
    "🌙 Как прошёл сегодняшний день? Что запомнилось больше всего?",
    "🙏 Кому или чему ты сегодня благодарен?",
    "🏆 Чем ты сегодня можешь гордиться? Какие были успехи, даже маленькие?",
    "📖 Какой урок или вывод можно вынести из сегодняшнего дня?",
    "🗓 Какой у тебя план на завтра? Три главных дела.",
]

WEEKLY_QUESTIONS = [
    "📅 *Итоги недели*\n\nКак в целом прошла неделя? Чем запомнилась?",
    "😟 Что больше всего беспокоило тебя на этой неделе?",
    "😊 Чему больше всего радовался на этой неделе?",
    "🙏 Кому и чему ты был благодарен на прошедшей неделе?",
    "😔 О чём жалеешь за прошедшую неделю?",
]

MOTIVATIONS = [
    "Каждый доллар приближает тебя к цели. Так держать! 💪",
    "Дисциплина сегодня — свобода завтра. Ты молодец! 🔥",
    "Маленькие шаги ведут к большим результатам. Продолжай! 🚀",
    "Ты уже ближе к цели, чем вчера. Не останавливайся! ⚡",
    "Богатство строится по кирпичику. Ты кладёшь свой! 🏆",
]




# =====================
# БАЗА ДАННЫХ (Supabase REST API)
# =====================

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def sb_get(table, params=None):
    resp = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=sb_headers(), params=params, timeout=10)
    return resp.json() if resp.ok else []


def sb_upsert(table, data, on_conflict="id"):
    headers = sb_headers()
    headers["Prefer"] = f"resolution=merge-duplicates,return=representation"
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}",
        headers=headers,
        json=data,
        timeout=10,
    )
    if not resp.ok:
        logger.error(f"sb_upsert {table} error: {resp.status_code} {resp.text}")
    return resp.ok


def init_db():
    """Проверяем подключение к Supabase."""
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/journal", headers=sb_headers(), params={"limit": 1}, timeout=10)
        if resp.status_code == 404:
            logger.warning("Таблицы не найдены — создай их в Supabase SQL Editor")
        else:
            logger.info("Supabase подключён успешно.")
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")


# =====================
# ЖУРНАЛ РЕФЛЕКСИИ
# =====================

def save_entry(date_str, answers):
    sb_upsert("journal", {
        "date": date_str,
        "saved_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        "day_text": answers.get("day", ""),
        "gratitude": answers.get("gratitude", ""),
        "self_gratitude": answers.get("self_gratitude", ""),
        "lesson": answers.get("lesson", ""),
        "plan": answers.get("plan", ""),
        "plan_review": answers.get("plan_review", ""),
    }, on_conflict="date")


def get_yesterday_plan():
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    # Берём последние записи до сегодня и находим первую с непустым планом
    rows = sb_get("journal", {"date": f"lt.{today}", "order": "date.desc", "limit": "10"})
    for row in rows:
        plan = (row.get("plan") or "").strip()
        if plan:
            return row["date"], plan
    return None, None


def get_monthly_gratitude():
    month = datetime.now(TIMEZONE).strftime("%Y-%m")
    rows = sb_get("journal", {"date": f"like.{month}%", "order": "date.asc"})
    return [(r["date"], r["gratitude"]) for r in rows if (r.get("gratitude") or "").strip()]


def get_journal_history():
    return sb_get("journal", {"order": "date.desc", "limit": "7"})


# =====================
# ЕЖЕНЕДЕЛЬНЫЙ ЖУРНАЛ
# =====================

def get_current_week():
    """Возвращает строку текущей недели в формате YYYY-WNN."""
    now = datetime.now(TIMEZONE)
    return now.strftime("%Y-W%W")

def get_last_week():
    """Возвращает строку прошлой недели."""
    now = datetime.now(TIMEZONE)
    last = now - timedelta(days=7)
    return last.strftime("%Y-W%W")

def save_weekly_entry(week, answers):
    sb_upsert("weekly_journal", {
        "week": week,
        "saved_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        "summary": answers.get("summary", ""),
        "worries": answers.get("worries", ""),
        "joys": answers.get("joys", ""),
        "gratitude": answers.get("gratitude", ""),
        "regrets": answers.get("regrets", ""),
        "plan": answers.get("plan", ""),
        "plan_review": answers.get("plan_review", ""),
    }, on_conflict="week")

def get_weekly_plan(week):
    rows = sb_get("weekly_journal", {"week": f"eq.{week}"})
    if rows:
        return rows[0].get("plan", "")
    return None


def make_weekly_ai_summary(weekly_answers):
    """AI-сводка недели: дневные записи за 7 дней + ответы /week → сводка с паттернами."""
    today = datetime.now(TIMEZONE)
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = sb_get("journal", {"date": f"gte.{week_ago}", "order": "date.asc"})

    daily_text = ""
    for r in rows:
        parts = []
        if r.get("day_text"):
            parts.append(f"день: {r['day_text']}")
        if r.get("self_gratitude"):
            parts.append(f"гордость/успехи: {r['self_gratitude']}")
        if r.get("gratitude"):
            parts.append(f"благодарность: {r['gratitude']}")
        if r.get("lesson"):
            parts.append(f"урок: {r['lesson']}")
        if parts:
            daily_text += f"\n{r['date']}: " + "; ".join(parts)

    weekly_text = (
        f"Итоги: {weekly_answers.get('summary', '')}\n"
        f"Беспокоило: {weekly_answers.get('worries', '')}\n"
        f"Радовало: {weekly_answers.get('joys', '')}\n"
        f"Благодарность: {weekly_answers.get('gratitude', '')}\n"
        f"Сожаления: {weekly_answers.get('regrets', '')}"
    )

    if not daily_text and not weekly_text.strip():
        return None

    prompt = (
        "Ты — внимательный и поддерживающий помощник по саморефлексии. "
        "Вот записи человека за прошедшую неделю.\n\n"
        f"Ежедневные записи:{daily_text or ' (нет)'}\n\n"
        f"Недельные итоги:\n{weekly_text}\n\n"
        "Сделай тёплую, но честную сводку недели (без воды, по делу):\n"
        "1. Чем человек может гордиться за неделю — 2-3 конкретных пункта из его записей.\n"
        "2. Какие повторяющиеся темы, настроения или паттерны заметны (и хорошие, и тревожные).\n"
        "3. Одно мягкое наблюдение или вопрос для размышления на следующую неделю.\n\n"
        "Пиши на «ты», живым языком, 6-10 предложений. Без markdown-заголовков."
    )
    summary = _ask_claude(prompt, max_tokens=1500)
    return summary or None

def get_last_week_plan():
    last_week = get_last_week()
    rows = sb_get("weekly_journal", {"week": f"eq.{last_week}"})
    if rows:
        return rows[0].get("plan", "")
    return None


# =====================
# ВИЗА
# =====================

def save_visa(entry_date, expiry_date):
    entry = datetime.strptime(entry_date, "%d.%m.%Y")
    expiry = datetime.strptime(expiry_date, "%d.%m.%Y")
    days = (expiry - entry).days
    sb_upsert("visa", {"id": 1, "entry_date": entry_date, "expiry_date": expiry_date, "days": days})
    return {"entry_date": entry_date, "expiry_date": expiry_date, "days": days}


def load_visa():
    rows = sb_get("visa", {"id": "eq.1"})
    return rows[0] if rows else None


def days_left(expiry_date_str):
    expiry = datetime.strptime(expiry_date_str, "%d.%m.%Y")
    today = datetime.now(TIMEZONE).replace(tzinfo=None)
    return (expiry - today).days


# =====================
# НАКОПЛЕНИЯ
# =====================

def load_savings():
    rows = sb_get("savings", {"id": "eq.1"})
    return rows[0]["balance"] if rows else 0


def save_savings_balance(balance):
    sb_upsert("savings", {"id": 1, "balance": balance})


def format_progress(balance, goal=SAVINGS_GOAL):
    pct = min(100, int(balance / goal * 100))
    filled = int(pct / 5)
    bar = "█" * filled + "░" * (20 - filled)
    remaining = max(0, goal - balance)
    return "\n".join([
        "💰 *Накопления*",
        "",
        f"`[{bar}]`",
        f"📊 {pct}% выполнено",
        f"💵 Накоплено: `{balance:.2f} USDT`",
        f"🎯 Цель: `{goal} USDT`",
        f"⏳ Осталось: `{remaining:.2f} USDT`",
    ])


# =====================
# КНИГИ
# =====================

def load_monthly_topic():
    month = datetime.now(TIMEZONE).strftime("%Y-%m")
    rows = sb_get("books_topic", {"month": f"eq.{month}"})
    return rows[0]["topic"] if rows else None


def save_monthly_topic(topic):
    month = datetime.now(TIMEZONE).strftime("%Y-%m")
    sb_upsert("books_topic", {"month": month, "topic": topic}, on_conflict="month")


def _ask_claude(prompt: str, max_tokens: int = 2000) -> str:
    """Запрос к Gemini (имя оставлено прежним для совместимости). Повтор при пустом ответе."""
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
                        "temperature": 0.7,
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
                    text = parts[0].get("text", "")
                    if text:
                        return text
            logger.error(f"Gemini empty (attempt {attempt + 1}): {str(data)[:300]}")
        except Exception as e:
            logger.error(f"Gemini error (attempt {attempt + 1}): {e}")
    return ""


def _get_books_from_claude(prompt: str) -> list:
    """Общий парсер: просим Gemini вернуть JSON-список книг."""
    raw = _ask_claude(prompt, max_tokens=8000)
    if not raw:
        logger.error("Books: пустой ответ от Gemini")
        return []
    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        # Резервный разбор: вытащить массив между первой [ и последней ]
        try:
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw[start:end + 1])
        except Exception as e:
            logger.error(f"Books JSON parse error: {e} | raw: {raw[:200]}")
        logger.error(f"Books JSON not found | raw: {raw[:200]}")
        return []


def get_weekly_books() -> list:
    return _get_books_from_claude(
        """Подбери 8 актуальных книг по темам: бизнес/предпринимательство, психология/саморазвитие, финансы/инвестиции, нон-фикшн/биографии.
Книги реальные, желательно последних 3-5 лет, разнообразие жанров.
Ответь СТРОГО в JSON-массиве без markdown, 8 объектов:
[{"title":"...","title_en":"...","author":"...","year":2023,"genre":"...","description":"2-3 предложения","goodreads_rating":"4.2/5","why_read":"одна причина прочитать сейчас"}]"""
    )


def get_books_by_topic(topic: str) -> list:
    return _get_books_from_claude(
        f"""Порекомендуй 5 лучших книг по теме: "{topic}".
Ответь СТРОГО в JSON-массиве без markdown, 5 объектов:
[{{"title":"...","title_en":"...","author":"...","year":2020,"genre":"...","description":"2-3 предложения","goodreads_rating":"4.3/5","why_read":"почему эта книга лучшая по теме"}}]"""
    )


def get_cover_url(title: str, author: str) -> str | None:
    """Обложка через Open Library — бесплатно, без ключа. Несколько попыток."""
    queries = []
    if title and author:
        queries.append(f"{title} {author}")
    if title:
        queries.append(title)
    for q in queries:
        try:
            resp = requests.get(
                "https://openlibrary.org/search.json",
                params={"q": q, "limit": 5, "fields": "cover_i"},
                timeout=8,
            )
            for doc in resp.json().get("docs", []):
                if doc.get("cover_i"):
                    return f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
        except Exception as e:
            logger.error(f"Open Library error: {e}")
    return None


def format_book(book: dict, num: int) -> str:
    emoji_map = {"бизнес": "💼", "предпринимательство": "🚀", "финансы": "💰",
                 "инвестиции": "📈", "психология": "🧠", "саморазвитие": "⚡",
                 "биографии": "👤", "нон-фикшн": "📖"}
    genre = book.get("genre", "").lower()
    icon = next((v for k, v in emoji_map.items() if k in genre), "📚")

    lines = [f"{icon} *{num}. {book.get('title', '—')}*", f"✍️ {book.get('author', '—')}"]
    if book.get("year") or book.get("genre"):
        lines.append(f"📅 {book.get('year', '')}  •  {book.get('genre', '')}".strip(" •"))
    if book.get("goodreads_rating"):
        lines.append(f"⭐ Goodreads: {book['goodreads_rating']}")
    if book.get("description"):
        lines.append(f"\n📝 {book['description']}")
    if book.get("why_read"):
        lines.append(f"\n💡 _{book['why_read']}_")
    return "\n".join(lines)


async def send_weekly_books(bot, chat_id):
    books = get_weekly_books()
    if not books:
        await bot.send_message(chat_id=chat_id, text="📚 Книжный бот заработает после добавления GEMINI_API_KEY.")
        return
    now = datetime.now(TIMEZONE).strftime("%d.%m.%Y")
    await bot.send_message(chat_id=chat_id,
        text=f"📚 *Книги на неделю — {now}*\nБизнес • Психология • Финансы • Нон-фикшн",
        parse_mode="Markdown")
    for i, book in enumerate(books, 1):
        caption = format_book(book, i)
        cover = get_cover_url(book.get("title_en") or book.get("title", ""), book.get("author", ""))
        try:
            if cover:
                await bot.send_photo(chat_id=chat_id, photo=cover, caption=caption, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
        except Exception:
            await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
        await asyncio.sleep(0.7)


async def send_recommendations(bot, chat_id, topic):
    books = get_books_by_topic(topic)
    if not books:
        await bot.send_message(chat_id=chat_id, text=f"📚 Рекомендации по теме *{topic}* заработают после добавления GEMINI_API_KEY.", parse_mode="Markdown")
        return
    await bot.send_message(chat_id=chat_id, text=f"📚 *Лучшие книги: {topic}*", parse_mode="Markdown")
    for i, book in enumerate(books, 1):
        caption = format_book(book, i)
        cover = get_cover_url(book.get("title_en") or book.get("title", ""), book.get("author", ""))
        try:
            if cover:
                await bot.send_photo(chat_id=chat_id, photo=cover, caption=caption, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
        except Exception:
            await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
        await asyncio.sleep(0.7)


def make_gratitude_summary(entries, month_name):
    if not entries:
        return "За этот месяц записей ещё нет."
    all_text = "\n".join(f"- {g}" for _, g in entries)
    if GEMINI_API_KEY:
        summary = _ask_claude(
            f"Записи благодарности за {month_name}:\n{all_text}\n\nТезисная сводка: кому благодарил чаще, за что, общий тон. 5-8 предложений.",
            max_tokens=500,
        )
        if summary:
            return f"🙏 *Благодарности за {month_name}*\n\n{summary}"
    text = f"🙏 *Благодарности за {month_name}*\n\nВсего записей: {len(entries)}\n\n"
    for date_str, g in entries[-5:]:
        text += f"_{date_str}_: {g[:120]}\n\n"
    return text


# =====================
# КУРСЫ ВАЛЮТ
# =====================

def _yahoo_price(symbol: str) -> float | None:
    """Цена через Yahoo Finance — без ключа."""
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        result = resp.json()["chart"]["result"][0]
        return result["meta"]["regularMarketPrice"]
    except Exception as e:
        logger.error(f"Yahoo Finance {symbol} error: {e}")
        return None


def _moex_index() -> float | None:
    """Индекс Мосбиржи (IMOEX) через официальный API."""
    try:
        resp = requests.get(
            "https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json",
            params={"iss.meta": "off", "iss.only": "marketdata"},
            timeout=10,
        )
        data = resp.json()["marketdata"]
        columns = data["columns"]
        rows = data["data"]
        if rows:
            idx = columns.index("CURRENTVALUE")
            return rows[0][idx]
    except Exception as e:
        logger.error(f"MOEX error: {e}")
    return None


def get_rates():
    try:
        # Крипта
        btc_resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10,
        )
        btc_usd = btc_resp.json()["bitcoin"]["usd"]

        # Валюты
        fx_resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        fx = fx_resp.json()["rates"]
        rub_per_usd = fx["RUB"]
        rub_per_thb = rub_per_usd / fx["THB"]

        # Золото, S&P500, Мосбиржа
        gold_usd = _yahoo_price("GC=F")       # Gold Futures
        sp500 = _yahoo_price("^GSPC")         # S&P 500
        moex = _moex_index()

        return {
            "btc_usd": btc_usd,
            "rub_per_usd": rub_per_usd,
            "rub_per_thb": rub_per_thb,
            "gold_usd": gold_usd,
            "sp500": sp500,
            "moex": moex,
        }
    except Exception as e:
        logger.error(f"Rates error: {e}")
        return None


def format_rates(rates):
    if not rates:
        return "❌ Не удалось получить курсы."
    now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")
    btc_str = f"{rates['btc_usd']:,.0f}".replace(",", " ")

    lines = [f"📊 *Курсы на {now}*\n"]

    # Крипта и валюты
    lines.append(f"₿ *Bitcoin:* `${btc_str}`")
    lines.append(f"💵 *Доллар:* `{rates['rub_per_usd']:.2f} ₽`")
    lines.append(f"🇹🇭 *Бат:* `{rates['rub_per_thb']:.2f} ₽`")

    # Рынки
    if rates.get("gold_usd"):
        gold_str = f"{rates['gold_usd']:,.0f}".replace(",", " ")
        lines.append(f"🥇 *Золото:* `${gold_str}/oz`")
    if rates.get("sp500"):
        sp_str = f"{rates['sp500']:,.0f}".replace(",", " ")
        lines.append(f"📈 *S&P 500:* `{sp_str}`")
    if rates.get("moex"):
        moex_str = f"{rates['moex']:,.0f}".replace(",", " ")
        lines.append(f"🇷🇺 *Мосбиржа:* `{moex_str}`")

    return "\n".join(lines)


# =====================
# КИНО
# =====================

def get_new_movies(limit=8):
    try:
        resp = requests.get(f"{TMDB_BASE}/movie/now_playing", params={"api_key": TMDB_API_KEY, "language": "ru-RU", "region": "US", "page": 1}, timeout=10)
        return resp.json().get("results", [])[:limit]
    except Exception as e:
        logger.error(f"TMDB error: {e}")
        return []


def get_movie_details(tmdb_id):
    try:
        detail = requests.get(f"{TMDB_BASE}/movie/{tmdb_id}", params={"api_key": TMDB_API_KEY, "language": "ru-RU"}, timeout=10).json()
        credits = requests.get(f"{TMDB_BASE}/movie/{tmdb_id}/credits", params={"api_key": TMDB_API_KEY, "language": "ru-RU"}, timeout=10).json()
        cast = credits.get("cast", [])[:3]
        actors = ", ".join(a["name"] for a in cast) if cast else "—"
        genres = ", ".join(g["name"] for g in detail.get("genres", [])[:3]) or "—"
        overview = detail.get("overview", "")
        if len(overview) > 150:
            overview = overview[:150] + "..."
        return {"genres": genres, "actors": actors, "overview": overview, "imdb_id": detail.get("imdb_id", "")}
    except Exception as e:
        logger.error(f"TMDB details error: {e}")
        return {"genres": "—", "actors": "—", "overview": "—", "imdb_id": ""}


def get_omdb_ratings(imdb_id, title):
    try:
        params = {"apikey": OMDB_API_KEY}
        if imdb_id:
            params["i"] = imdb_id
        else:
            params["t"] = title
        data = requests.get("https://www.omdbapi.com/", params=params, timeout=10).json()
        result = {}
        if data.get("imdbRating") and data["imdbRating"] != "N/A":
            result["imdb"] = data["imdbRating"]
        for r in data.get("Ratings", []):
            if "Rotten Tomatoes" in r["Source"]:
                result["rt"] = r["Value"]
        return result
    except Exception as e:
        logger.error(f"OMDB error: {e}")
        return {}


def get_kp_rating(title, year=None):
    try:
        params = {"query": title, "limit": 1}
        if year:
            params["year"] = year
        resp = requests.get("https://api.kinopoisk.dev/v1.4/movie/search", headers={"X-API-KEY": KP_API_KEY}, params=params, timeout=10)
        docs = resp.json().get("docs", [])
        if docs:
            kp = docs[0].get("rating", {}).get("kp")
            if kp and kp > 0:
                return f"{kp:.1f}"
    except Exception as e:
        logger.error(f"KP error: {e}")
    return None


def format_movie_caption(movie, details, omdb, kp_rating):
    title = movie.get("title", "—")
    original = movie.get("original_title", "")
    year = movie.get("release_date", "")[:4] if movie.get("release_date") else ""
    tmdb_rating = movie.get("vote_average", 0)
    caption = f"🎬 *{title}*"
    if original and original != title:
        caption += f" / _{original}_"
    if year:
        caption += f" ({year})"
    caption += "\n\n"
    if details.get("genres"):
        caption += f"🎭 {details['genres']}\n"
    if details.get("overview"):
        caption += f"📝 {details['overview']}\n"
    if details.get("actors"):
        caption += f"👥 {details['actors']}\n"
    caption += "\n*Рейтинги:*\n"
    if tmdb_rating > 0:
        caption += f"🎥 TMDB: `{tmdb_rating:.1f}/10`\n"
    if omdb.get("imdb"):
        caption += f"⭐ IMDb: `{omdb['imdb']}/10`\n"
    if omdb.get("rt"):
        caption += f"🍅 Rotten Tomatoes: `{omdb['rt']}`\n"
    if kp_rating:
        caption += f"🇷🇺 Кинопоиск: `{kp_rating}/10`\n"
    return caption


async def send_movies(bot, chat_id, period_label="недели"):
    await bot.send_message(chat_id=chat_id, text=f"🎬 *Новинки кино {period_label}*\n\nСобираю данные...", parse_mode="Markdown")
    movies = get_new_movies(limit=8)
    if not movies:
        await bot.send_message(chat_id=chat_id, text="❌ Не удалось получить список фильмов.")
        return
    for movie in movies:
        try:
            tmdb_id = movie["id"]
            title = movie.get("title", "")
            year = movie.get("release_date", "")[:4]
            poster_path = movie.get("poster_path")
            details = get_movie_details(tmdb_id)
            omdb = get_omdb_ratings(details.get("imdb_id", ""), title)
            kp = get_kp_rating(title, year)
            caption = format_movie_caption(movie, details, omdb, kp)
            if poster_path:
                await bot.send_photo(chat_id=chat_id, photo=f"{TMDB_IMG}{poster_path}", caption=caption, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error sending movie: {e}")
            continue


# =====================
# TODOIST
# =====================

def _todoist_get_all_tasks() -> list:
    """Получаем все активные задачи из Todoist."""
    resp = requests.get(
        f"{TODOIST_API}/tasks",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.error(f"Todoist tasks error: {resp.status_code} {resp.text}")
        return []
    data = resp.json()
    logger.info(f"Todoist raw type: {type(data)}, preview: {str(data)[:300]}")
    if isinstance(data, dict):
        tasks = [t for t in data.get("results", []) if isinstance(t, dict)]
    else:
        tasks = [t for t in data if isinstance(t, dict)] if isinstance(data, list) else []
    logger.info(f"Todoist tasks: {len(tasks)}, due fields: {[t.get('due') for t in tasks[:5]]}")
    return tasks


def _parse_due_date(due: dict) -> str:
    """Возвращает строку даты YYYY-MM-DD из поля due."""
    return str(due.get("date", ""))[:10]


def _parse_due_time(due: dict):
    """Возвращает локальный datetime если в due есть время, иначе None."""
    date_str = due.get("date", "")
    if not date_str or len(date_str) <= 10:
        return None  # только дата, без времени
    try:
        # Todoist v1: время хранится в поле date как "2026-05-28T10:00:00"
        # может быть без timezone — считаем UTC
        if "+" not in date_str and date_str.endswith("Z"):
            date_str = date_str.replace("Z", "+00:00")
        elif "+" not in date_str and len(date_str) > 10:
            date_str = date_str + "+00:00"
        return datetime.fromisoformat(date_str).astimezone(TIMEZONE)
    except Exception as e:
        logger.error(f"Due time parse error: {e}, value: {date_str}")
        return None


def get_today_tasks() -> list:
    """Задачи как в разделе 'Сегодня' Todoist — через filter эндпоинт."""
    resp = requests.get(
        f"{TODOIST_API}/tasks/filter",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
        params={"query": "today | overdue"},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.error(f"Todoist filter error: {resp.status_code} {resp.text}")
        return []
    data = resp.json()
    if isinstance(data, dict):
        tasks = [t for t in data.get("results", []) if isinstance(t, dict)]
    else:
        tasks = [t for t in data if isinstance(t, dict)] if isinstance(data, list) else []
    logger.info(f"Todoist filter 'today | overdue' returned: {len(tasks)} tasks")
    def sort_key(t):
        due = t.get("due") or {}
        return due.get("date") or "0"
    return sorted(tasks, key=sort_key)


def get_tasks_due_in_one_hour() -> list:
    """Задачи с точным временем дедлайна через ~1 час (±5 минут)."""
    now = datetime.now(TIMEZONE)
    target_start = now + timedelta(minutes=55)
    target_end = now + timedelta(minutes=65)
    result = []
    for task in _todoist_get_all_tasks():
        due = task.get("due")
        if not due:
            continue
        due_local = _parse_due_time(due)
        if due_local and target_start <= due_local <= target_end:
            result.append(task)
    return result


def format_tasks(tasks: list, header: str = "Задачи на сегодня") -> str:
    if not tasks:
        return "✅ На сегодня задач нет!"
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    text = f"📋 *{header} ({len(tasks)}):*\n\n"
    for i, task in enumerate(tasks, 1):
        priority_emoji = {1: "", 2: "🔵", 3: "🟡", 4: "🔴"}.get(task.get("priority", 1), "")
        due = task.get("due") or {}
        due_date = _parse_due_date(due)
        due_local = _parse_due_time(due)
        due_time = f" `{due_local.strftime('%H:%M')}`" if due_local else ""
        overdue = " ⚠️" if due_date and due_date < today else ""
        text += f"{i}.{priority_emoji}{due_time}{overdue} {task.get('content', '—')}\n"
    return text


# =====================
# ХЕНДЛЕРЫ — РЕФЛЕКСИЯ
# =====================

async def start_reflection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "Привет! Я твой бот для рефлексии 🌙\n\n"
        "/ask — начать рефлексию\n"
        "/plan — план на сегодня\n"
        "/history — последние 7 записей\n"
        "/gratitude — сводка благодарностей"
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
    return Q_SELF


async def answer_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["self_gratitude"] = update.message.text
    await update.message.reply_text(QUESTIONS[3])
    return Q3


async def answer_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["lesson"] = update.message.text
    await update.message.reply_text(QUESTIONS[4])
    return Q4


async def answer_q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["plan"] = update.message.text
    date_str, yesterday_plan = get_yesterday_plan()
    if yesterday_plan:
        await update.message.reply_text(
            f"📋 *Твой план со вчера ({date_str}):*\n\n{yesterday_plan}\n\n✅ Удалось выполнить что-то из списка?",
            parse_mode="Markdown"
        )
        return Q5
    date_str = context.user_data["date"]
    save_entry(date_str, context.user_data["answers"])
    await update.message.reply_text(f"✅ Всё записано. Хорошего вечера!\n\nЗапись за {date_str} сохранена.")
    return ConversationHandler.END


async def answer_plan_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["plan_review"] = update.message.text
    date_str = context.user_data["date"]
    save_entry(date_str, context.user_data["answers"])
    await update.message.reply_text(f"✅ Всё записано. Хорошего вечера!\n\nЗапись за {date_str} сохранена.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    rows = get_journal_history()
    if not rows:
        await update.message.reply_text("Дневник пока пустой.")
        return
    text = "📔 *Последние записи:*\n\n"
    for row in rows:
        text += f"*{row['date']}*\n"
        if row.get("plan_review"):
            text += f"✅ {row['plan_review']}\n"
        text += f"🌙 {row.get('day_text') or '—'}\n"
        text += f"🙏 {row.get('gratitude') or '—'}\n"
        text += f"🏆 {row.get('self_gratitude') or '—'}\n"
        text += f"📖 {row.get('lesson') or '—'}\n"
        text += f"🗓 {row.get('plan') or '—'}\n"
        text += "─────────────\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    date_str, plan = get_yesterday_plan()
    if plan:
        await update.message.reply_text(f"📋 *План на сегодня:*\n\n{plan}", parse_mode="Markdown")
    else:
        await update.message.reply_text("Плана нет — вчера не было записи.")


async def gratitude_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    entries = get_monthly_gratitude()
    month_name = datetime.now(TIMEZONE).strftime("%B %Y")
    await update.message.reply_text(make_gratitude_summary(entries, month_name), parse_mode="Markdown")


async def morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    date_str, plan = get_yesterday_plan()
    if plan:
        await context.bot.send_message(chat_id=MY_CHAT_ID, text=f"☀️ Доброе утро!\n\n*План на сегодня:*\n\n{plan}", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=MY_CHAT_ID, text="☀️ Доброе утро! Плана на сегодня нет.")


async def evening_questions(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=MY_CHAT_ID, text="Добрый вечер! Время для рефлексии 🌙\n\nНапиши /ask чтобы начать.")


async def monthly_gratitude_report(context: ContextTypes.DEFAULT_TYPE):
    entries = get_monthly_gratitude()
    month_name = datetime.now(TIMEZONE).strftime("%B %Y")
    await context.bot.send_message(chat_id=MY_CHAT_ID, text=make_gratitude_summary(entries, month_name), parse_mode="Markdown")


# =====================
# ХЕНДЛЕРЫ — КУРСЫ
# =====================

async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != BYBIT_CHAT_ID:
        return
    await update.message.reply_text(format_rates(get_rates()), parse_mode="Markdown")


async def bybit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != BYBIT_CHAT_ID:
        return
    await update.message.reply_text("Привет! Я слежу за курсами 📊\n\nКаждое утро в 08:00 присылаю курсы.\n\n/rates — курсы прямо сейчас")


async def morning_rates(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=BYBIT_CHAT_ID, text="☀️ *Доброе утро!*\n\n" + format_rates(get_rates()), parse_mode="Markdown")


# =====================
# ХЕНДЛЕРЫ — КИНО
# =====================

async def cinema_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text("Привет! Я слежу за новинками кино 🎬\n\n/movies — получить подборку прямо сейчас")


async def movies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    try:
        await update.message.reply_text("🎬 Запрашиваю новинки... ⏳")
        await send_movies(context.bot, MY_CHAT_ID, "этой недели")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def weekly_movies(context: ContextTypes.DEFAULT_TYPE):
    await send_movies(context.bot, MY_CHAT_ID, "этой недели")


async def monthly_movies(context: ContextTypes.DEFAULT_TYPE):
    await send_movies(context.bot, MY_CHAT_ID, "этого месяца")


# =====================
# ХЕНДЛЕРЫ — ВИЗА
# =====================

async def visa_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    visa = load_visa()
    text = "🇹🇭 *Визовый будильник*\n\n/set — задать визу\n/vstatus — статус визы\n"
    if visa:
        left = days_left(visa["expiry_date"])
        text += f"\n📅 Виза истекает: *{visa['expiry_date']}*\nОсталось: *{left} дн.*"
    await update.message.reply_text(text, parse_mode="Markdown")


async def set_visa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text("📅 Введи дату въезда в формате ДД.ММ.ГГГГ\nНапример: `15.05.2026`", parse_mode="Markdown")
    return ENTER_DATE


async def enter_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["entry_date"] = text
        await update.message.reply_text("✅ Дата въезда принята.\n\nТеперь введи дату окончания штампа в формате ДД.ММ.ГГГГ\nНапример: `14.06.2026`", parse_mode="Markdown")
        return ENTER_EXPIRY
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введи дату в формате ДД.ММ.ГГГГ")
        return ENTER_DATE


async def enter_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        expiry = datetime.strptime(text, "%d.%m.%Y")
        entry_date = context.user_data["entry_date"]
        entry = datetime.strptime(entry_date, "%d.%m.%Y")
        if expiry <= entry:
            await update.message.reply_text("❌ Дата окончания должна быть позже даты въезда.")
            return ENTER_EXPIRY
        visa = save_visa(entry_date, text)
        left = days_left(visa["expiry_date"])
        await update.message.reply_text(
            f"✅ *Виза сохранена!*\n\n📅 Въезд: {entry_date}\n🔴 Истекает: *{text}*\n⏳ Срок: {visa['days']} дней\n📊 Осталось: *{left} дн.*\n\nБуду напоминать за 14, 7, 3 и 1 день.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введи дату в формате ДД.ММ.ГГГГ")
        return ENTER_EXPIRY


async def vstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    visa = load_visa()
    if not visa:
        await update.message.reply_text("Виза не задана. Используй /set")
        return
    left = days_left(visa["expiry_date"])
    if left < 0:
        emoji, status_text = "🚨", f"ПРОСРОЧЕНА на {abs(left)} дней!"
    elif left == 0:
        emoji, status_text = "🚨", "истекает СЕГОДНЯ!"
    elif left <= 3:
        emoji, status_text = "🔴", f"осталось *{left} дн.* — срочно!"
    elif left <= 7:
        emoji, status_text = "🟠", f"осталось *{left} дн.*"
    elif left <= 14:
        emoji, status_text = "🟡", f"осталось *{left} дн.*"
    else:
        emoji, status_text = "🟢", f"осталось *{left} дн.*"
    total = visa["days"]
    used = total - max(0, left)
    pct = max(0, min(100, int(used / total * 100)))
    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
    await update.message.reply_text(
        f"{emoji} *Статус визы*\n\n📅 Въезд: {visa['entry_date']}\n🔴 Истекает: {visa['expiry_date']}\n⏳ {status_text}\n\n`[{bar}]` {pct}% использовано",
        parse_mode="Markdown"
    )


async def check_visa_reminders(context: ContextTypes.DEFAULT_TYPE):
    visa = load_visa()
    if not visa:
        return
    left = days_left(visa["expiry_date"])
    msgs = {
        14: "🟡 *Напоминание о визе*\n\nДо конца визы осталось *14 дней*. Начинай думать о продлении.",
        7: "🟠 *Эй, пора планировать бордер ран!*\n\nДо конца визы осталось *7 дней*.",
        3: "🔴 *Виза истекает через 3 дня!*\n\nПора планировать бордер ран!",
        1: "🚨 *Завтра истекает виза!*\n\nОстался *1 день*. Срочно планируй бордер ран или продление!",
    }
    if left in msgs:
        await context.bot.send_message(chat_id=MY_CHAT_ID, text=msgs[left] + f"\n\n📅 Истекает: {visa['expiry_date']}", parse_mode="Markdown")
    elif left < 0:
        await context.bot.send_message(chat_id=MY_CHAT_ID, text=f"🚨 *ВИЗА ПРОСРОЧЕНА!*\n\nПросрочка: {abs(left)} дней.", parse_mode="Markdown")


# =====================
# ХЕНДЛЕРЫ — TODOIST
# =====================

async def todoist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "Привет! Я твой Todoist-помощник 📋\n\n"
        "Просто напиши задачу — добавлю в Inbox.\n\n"
        "/tasks — задачи на сегодня\n"
        "/inbox — все задачи без даты"
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    tasks = get_today_tasks()
    await update.message.reply_text(format_tasks(tasks), parse_mode="Markdown")


async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    all_tasks = _todoist_get_all_tasks()
    inbox = [t for t in all_tasks if not t.get("due")]
    if not inbox:
        await update.message.reply_text("📥 Inbox пуст!")
        return
    text = f"📥 *Inbox ({len(inbox)}):*\n\n"
    for i, task in enumerate(inbox[:20], 1):
        text += f"{i}. {task.get('content', '—')}\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def todoist_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    text = update.message.text.strip()
    if not text:
        return
    resp = requests.post(
        f"{TODOIST_API}/tasks",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
        json={"content": text},
        timeout=10,
    )
    if resp.status_code == 200:
        await update.message.reply_text(f"✅ Добавлено в Inbox:\n_{text}_", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Ошибка {resp.status_code}: {resp.text[:200]}")


async def morning_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Утренняя рассылка в 09:00 — только задачи с датой на сегодня."""
    tasks = get_today_tasks()
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="☀️ *Доброе утро!*\n\n" + format_tasks(tasks),
        parse_mode="Markdown",
    )


async def deadline_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Каждые 30 минут проверяем задачи с дедлайном через ~1 час."""
    tasks = get_tasks_due_in_one_hour()
    if not tasks:
        return
    for task in tasks:
        due = task.get("due", {}) or {}
        due_local = _parse_due_time(due)
        if not due_local:
            continue
        priority_emoji = {1: "", 2: "🔵", 3: "🟡", 4: "🔴"}.get(task.get("priority", 1), "")
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=(
                f"⏰ *Напоминание — через 1 час:*\n\n"
                f"{priority_emoji} {task.get('content', '—')}\n"
                f"🕐 Дедлайн: `{due_local.strftime('%H:%M')}`"
            ),
            parse_mode="Markdown",
        )


# =====================
# ДНИ РОЖДЕНИЯ
# =====================

def _get_birthday_project_id() -> str | None:
    """Находит ID проекта 'Дни рождения' по названию."""
    try:
        resp = requests.get(
            f"{TODOIST_API}/projects",
            headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f"Todoist projects error: {resp.status_code}")
            return None
        data = resp.json()
        projects = data.get("results", []) if isinstance(data, dict) else data
        for p in projects:
            if isinstance(p, dict) and "дни рождения" in p.get("name", "").lower():
                return p.get("id")
    except Exception as e:
        logger.error(f"Birthday project lookup error: {e}")
    return None


def get_birthday_tasks() -> list:
    """Все задачи из проекта 'Дни рождения'."""
    project_id = _get_birthday_project_id()
    if not project_id:
        return []
    try:
        resp = requests.get(
            f"{TODOIST_API}/tasks",
            headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
            params={"project_id": project_id},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        tasks = data.get("results", []) if isinstance(data, dict) else data
        return [t for t in tasks if isinstance(t, dict)]
    except Exception as e:
        logger.error(f"Birthday tasks error: {e}")
        return []


async def check_birthday_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневно в 09:00 — напоминания за 7, 1 и 0 дней до ДР."""
    today = datetime.now(TIMEZONE).date()
    for task in get_birthday_tasks():
        due = task.get("due")
        if not due:
            continue
        due_date_str = _parse_due_date(due)
        if not due_date_str:
            continue
        try:
            bday = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_until = (bday - today).days
        name = task.get("content", "—")

        if days_until == 7:
            await context.bot.send_message(
                chat_id=MY_CHAT_ID,
                text=f"🎂 *Через неделю день рождения!*\n\n{name}\n\n📅 {due_date_str}\n\nЕсть время выбрать подарок 🎁",
                parse_mode="Markdown",
            )
        elif days_until == 1:
            await context.bot.send_message(
                chat_id=MY_CHAT_ID,
                text=f"🎉 *Завтра день рождения!*\n\n{name}\n\nНе забудь поздравить! 🥳",
                parse_mode="Markdown",
            )
        elif days_until == 0:
            await context.bot.send_message(
                chat_id=MY_CHAT_ID,
                text=f"🎈 *Сегодня день рождения!*\n\n{name}\n\nСамое время поздравить! 🎊",
                parse_mode="Markdown",
            )


async def birthdays_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ближайшие дни рождения."""
    if update.effective_chat.id != MY_CHAT_ID:
        return
    today = datetime.now(TIMEZONE).date()
    upcoming = []
    for task in get_birthday_tasks():
        due = task.get("due")
        if not due:
            continue
        due_date_str = _parse_due_date(due)
        if not due_date_str:
            continue
        try:
            bday = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_until = (bday - today).days
        if 0 <= days_until <= 60:
            upcoming.append((days_until, task.get("content", "—"), due_date_str))
    if not upcoming:
        await update.message.reply_text("🎂 В ближайшие 2 месяца дней рождения нет.")
        return
    upcoming.sort()
    text = "🎂 *Ближайшие дни рождения:*\n\n"
    for days, name, date_str in upcoming:
        if days == 0:
            when = "сегодня! 🎉"
        elif days == 1:
            when = "завтра"
        else:
            when = f"через {days} дн."
        text += f"• {name} — {when}\n"
    await update.message.reply_text(text, parse_mode="Markdown")


# =====================
# ХЕНДЛЕРЫ — НАКОПЛЕНИЯ
# =====================

async def savings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    balance = load_savings()
    text = "💰 *Трекер накоплений*\n\nКоманды:\n/balance — текущий баланс\n\nПополнение: напиши `+100`\nСписание: напиши `-50`\n\n"
    text += format_progress(balance)
    await update.message.reply_text(text, parse_mode="Markdown")


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    balance = load_savings()
    await update.message.reply_text(format_progress(balance), parse_mode="Markdown")


async def savings_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    text = update.message.text.strip()
    if not (text.startswith("+") or text.startswith("-")):
        await update.message.reply_text("Напиши `+100` чтобы пополнить или `-50` чтобы списать.", parse_mode="Markdown")
        return
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Напиши `+100` или `-50`", parse_mode="Markdown")
        return
    old_balance = load_savings()
    new_balance = old_balance + amount
    if new_balance < 0:
        await update.message.reply_text("❌ Баланс не может быть отрицательным.")
        return
    save_savings_balance(new_balance)
    if old_balance < SAVINGS_GOAL and new_balance >= SAVINGS_GOAL:
        await update.message.reply_text(f"🎉🏆 *ЦЕЛЬ ДОСТИГНУТА!* 🏆🎉\n\nТы накопил `{new_balance:.2f} USDT`!\n\nЭто невероятно! Дисциплина и терпение работают. Ты заслужил это! 🚀💪", parse_mode="Markdown")
        return
    motivation = random.choice(MOTIVATIONS)
    action = "Пополнено" if amount > 0 else "Списано"
    emoji = "✅" if amount > 0 else "📤"
    msg = f"{emoji} {action} `{abs(amount):.2f} USDT`\n\n" + format_progress(new_balance) + f"\n\n_{motivation}_"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def weekly_savings_report(context: ContextTypes.DEFAULT_TYPE):
    balance = load_savings()
    motivation = random.choice(MOTIVATIONS)
    text = "📅 *Еженедельный отчёт по накоплениям*\n\n" + format_progress(balance) + f"\n\n_{motivation}_"
    await context.bot.send_message(chat_id=MY_CHAT_ID, text=text, parse_mode="Markdown")


# =====================
# ХЕНДЛЕРЫ — КНИГИ
# =====================

async def books_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text("📚 *Книжный бот*\n\nКаждый понедельник в 09:00 — новинки.\n1-го числа — спрошу тему месяца.\n\n/books — подборка прямо сейчас\n/recommend [тема] — лучшие книги по теме", parse_mode="Markdown")


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text("📚 Ищу книжные новинки... ⏳")
    await send_weekly_books(context.bot, MY_CHAT_ID)


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text("Напиши тему: `/recommend финансы`", parse_mode="Markdown")
        return
    await update.message.reply_text(f"🔍 Ищу лучшие книги по теме: *{topic}*...", parse_mode="Markdown")
    await send_recommendations(context.bot, MY_CHAT_ID, topic)


async def books_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    if context.user_data.get("waiting_topic"):
        topic = update.message.text.strip()
        save_monthly_topic(topic)
        context.user_data.pop("waiting_topic", None)
        await update.message.reply_text(f"✅ Тема месяца: *{topic}*\n\nИщу лучшие книги...", parse_mode="Markdown")
        await send_recommendations(context.bot, MY_CHAT_ID, topic)
    else:
        await update.message.reply_text("Используй /books для новинок или /recommend [тема] для рекомендаций.")


async def weekly_books_report(context: ContextTypes.DEFAULT_TYPE):
    await send_weekly_books(context.bot, MY_CHAT_ID)


async def monthly_books_question(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_topic"] = True
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="📚 *Книжный вопрос месяца*\n\nНа какую тему ты хотел бы почитать книгу в этом месяце?\n\nПросто напиши тему в ответ.",
        parse_mode="Markdown"
    )



# =====================
# ХЕНДЛЕРЫ — ЕЖЕНЕДЕЛЬНАЯ РЕФЛЕКСИЯ
# =====================

async def weekly_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    context.user_data["weekly_answers"] = {}
    context.user_data["week"] = get_current_week()
    await update.message.reply_text(WEEKLY_QUESTIONS[0], parse_mode="Markdown")
    return WQ1

async def weekly_q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["summary"] = update.message.text
    await update.message.reply_text(WEEKLY_QUESTIONS[1])
    return WQ2

async def weekly_q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["worries"] = update.message.text
    await update.message.reply_text(WEEKLY_QUESTIONS[2])
    return WQ3

async def weekly_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["joys"] = update.message.text
    await update.message.reply_text(WEEKLY_QUESTIONS[3])
    return WQ4

async def weekly_q4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["gratitude"] = update.message.text
    await update.message.reply_text(WEEKLY_QUESTIONS[4])
    return WQ5

async def weekly_q5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["regrets"] = update.message.text
    
    # Показываем прошлонедельный план если есть
    last_plan = get_last_week_plan()
    if last_plan:
        await update.message.reply_text(
            f"📋 *Твои планы на эту неделю были:*\n\n{last_plan}\n\n✅ Удалось выполнить? Напиши коротко.",
            parse_mode="Markdown"
        )
        return WQ6
    else:
        await update.message.reply_text(
            "🗓 *Какие планы ставишь на следующую неделю?*\n\nНапиши список целей.",
            parse_mode="Markdown"
        )
        return WQ7

async def weekly_q6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["plan_review"] = update.message.text
    await update.message.reply_text(
        "🗓 *Какие планы ставишь на следующую неделю?*\n\nНапиши список целей.",
        parse_mode="Markdown"
    )
    return WQ7

async def weekly_q7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weekly_answers"]["plan"] = update.message.text
    week = context.user_data["week"]
    answers = context.user_data["weekly_answers"]
    save_weekly_entry(week, answers)
    await update.message.reply_text(
        f"✅ *Итоги недели сохранены!*\n\nГотовлю сводку за неделю... 🧠",
        parse_mode="Markdown"
    )
    summary = make_weekly_ai_summary(answers)
    if summary:
        await update.message.reply_text(
            f"📊 *Твоя неделя — взгляд со стороны*\n\n{summary}",
            parse_mode="Markdown"
        )
    await update.message.reply_text("Хорошей следующей недели! 💪")
    return ConversationHandler.END

async def weekly_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

async def weekly_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Воскресенье 22:00 — напоминание об итогах недели."""
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="🗓 Время подвести итоги недели!\n\nНапиши /week чтобы начать.",
    )

async def monday_plan_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Понедельник 08:00 — план на неделю."""
    plan = get_weekly_plan(get_current_week())
    if plan:
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=f"☀️ *Доброе утро! Планы на эту неделю:*\n\n{plan}",
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text="☀️ Доброе утро! Планов на эту неделю нет — заполни /week в воскресенье.",
        )

# =====================
# ЗАПУСК
# =====================

async def main():
    # Инициализируем базу данных
    init_db()

    # Бот саморефлексии
    reflection_app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q2)],
            Q_SELF: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_self)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_plan_review)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    weekly_conv = ConversationHandler(
        entry_points=[CommandHandler("week", weekly_ask)],
        states={
            WQ1: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q1)],
            WQ2: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q2)],
            WQ3: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q3)],
            WQ4: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q4)],
            WQ5: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q5)],
            WQ6: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q6)],
            WQ7: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_q7)],
        },
        fallbacks=[CommandHandler("cancel", weekly_cancel)],
    )

    reflection_app.add_handler(CommandHandler("start", start_reflection))
    reflection_app.add_handler(conv_handler)
    reflection_app.add_handler(weekly_conv)
    reflection_app.add_handler(CommandHandler("history", history))
    reflection_app.add_handler(CommandHandler("gratitude", gratitude_summary))
    reflection_app.add_handler(CommandHandler("plan", plan_command))
    reflection_app.job_queue.run_daily(evening_questions, time=dtime(hour=21, minute=0, tzinfo=TIMEZONE))
    reflection_app.job_queue.run_monthly(monthly_gratitude_report, when=dtime(hour=9, tzinfo=TIMEZONE), day=1)
    reflection_app.job_queue.run_daily(weekly_reminder, time=dtime(hour=22, minute=0, tzinfo=TIMEZONE), days=(6,))

    # Бот курсов
    rates_app = Application.builder().token(BYBIT_BOT_TOKEN).build()
    rates_app.add_handler(CommandHandler("start", bybit_start))
    rates_app.add_handler(CommandHandler("rates", rates_command))
    rates_app.job_queue.run_daily(morning_rates, time=dtime(hour=8, minute=0, tzinfo=TIMEZONE))

    # Бот кино
    cinema_app = Application.builder().token(CINEMA_BOT_TOKEN).build()
    cinema_app.add_handler(CommandHandler("start", cinema_start))
    cinema_app.add_handler(CommandHandler("movies", movies_command))
    cinema_app.job_queue.run_daily(weekly_movies, time=dtime(hour=22, minute=0, tzinfo=TIMEZONE), days=(5,))
    cinema_app.job_queue.run_monthly(monthly_movies, when=dtime(hour=20, tzinfo=TIMEZONE), day=1)

    # Визовый бот
    visa_app = Application.builder().token(VISA_BOT_TOKEN).build()
    visa_conv = ConversationHandler(
        entry_points=[CommandHandler("set", set_visa)],
        states={
            ENTER_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_date)],
            ENTER_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_expiry)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    visa_app.add_handler(CommandHandler("start", visa_start))
    visa_app.add_handler(CommandHandler("vstatus", vstatus))
    visa_app.add_handler(visa_conv)
    visa_app.job_queue.run_daily(check_visa_reminders, time=dtime(hour=10, minute=0, tzinfo=TIMEZONE))

    # Todoist бот
    todoist_app = Application.builder().token(TODOIST_BOT_TOKEN).build()
    todoist_app.add_handler(CommandHandler("start", todoist_start))
    todoist_app.add_handler(CommandHandler("tasks", tasks_command))
    todoist_app.add_handler(CommandHandler("inbox", inbox_command))
    todoist_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, todoist_handle_message))
    todoist_app.job_queue.run_daily(morning_tasks, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE))
    todoist_app.job_queue.run_repeating(deadline_reminder, interval=1800, first=60)  # каждые 30 минут
    todoist_app.add_handler(CommandHandler("birthdays", birthdays_command))
    todoist_app.job_queue.run_daily(check_birthday_reminders, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE))

    # Бот накоплений
    savings_app = Application.builder().token(SAVINGS_BOT_TOKEN).build()
    savings_app.add_handler(CommandHandler("start", savings_start))
    savings_app.add_handler(CommandHandler("balance", balance_command))
    savings_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, savings_handle_message))
    savings_app.job_queue.run_daily(weekly_savings_report, time=dtime(hour=20, minute=0, tzinfo=TIMEZONE), days=(6,))

    # Книжный бот
    books_app = Application.builder().token(BOOKS_BOT_TOKEN).build()
    books_app.add_handler(CommandHandler("start", books_start))
    books_app.add_handler(CommandHandler("books", books_command))
    books_app.add_handler(CommandHandler("recommend", recommend_command))
    books_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, books_handle_message))
    books_app.job_queue.run_daily(weekly_books_report, time=dtime(hour=9, minute=0, tzinfo=TIMEZONE), days=(0,))
    books_app.job_queue.run_monthly(monthly_books_question, when=dtime(hour=10, tzinfo=TIMEZONE), day=1)

    return [
        reflection_app, rates_app, cinema_app,
        visa_app, todoist_app, savings_app, books_app,
    ]


async def _run_standalone():
    """Автономный запуск bot.py отдельно (если не через main.py)."""
    apps = await main()
    async with apps[0], apps[1], apps[2], apps[3], apps[4], apps[5], apps[6]:
        for app in apps:
            await app.start()
        for app in apps:
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Все боты запущены.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_run_standalone())
