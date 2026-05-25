import os
import json
import logging
import requests
from datetime import datetime, timedelta, time as dtime
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
CINEMA_BOT_TOKEN = os.environ.get("CINEMA_BOT_TOKEN")
VISA_BOT_TOKEN = os.environ.get("VISA_BOT_TOKEN")
TODOIST_BOT_TOKEN = os.environ.get("TODOIST_BOT_TOKEN")
TODOIST_TOKEN = os.environ.get("TODOIST_TOKEN")
SAVINGS_BOT_TOKEN = os.environ.get("SAVINGS_BOT_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")
KP_API_KEY = os.environ.get("KP_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
JOURNAL_FILE = "journal.json"
VISA_FILE = "visa.json"

# Состояния диалогов
Q1, Q2, Q3, Q4, Q5 = range(5)
ENTER_DATE, ENTER_EXPIRY = range(2)

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
    journal = load_journal()
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    for date_str in sorted(journal.keys(), reverse=True):
        if date_str < today:
            plan = journal[date_str].get("answers", {}).get("plan", "")
            if plan:
                return date_str, plan
    return None, None


def get_monthly_gratitude_summary():
    journal = load_journal()
    current_month = datetime.now(TIMEZONE).strftime("%Y-%m")
    entries = []
    for date_str, entry in journal.items():
        if date_str.startswith(current_month):
            g = entry.get("answers", {}).get("gratitude", "")
            if g:
                entries.append((date_str, g))
    return entries


def make_gratitude_summary(entries, month_name):
    if not entries:
        return "За этот месяц записей ещё нет."
    all_text = "\n".join(f"- {g}" for _, g in entries)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 500, "messages": [{"role": "user", "content": f"Записи благодарности за {month_name}:\n{all_text}\n\nТезисная сводка: кому благодарил чаще, за что, общий тон. 5-8 предложений."}]},
                timeout=30,
            )
            summary = response.json()["content"][0]["text"]
            return f"🙏 *Благодарности за {month_name}*\n\n{summary}"
        except Exception as e:
            logger.error(f"Claude API error: {e}")
    text = f"🙏 *Благодарности за {month_name}*\n\nВсего записей: {len(entries)}\n\n"
    for date_str, g in entries[-5:]:
        text += f"_{date_str}_: {g[:120]}\n\n"
    return text


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
    return Q3


async def answer_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"]["lesson"] = update.message.text
    await update.message.reply_text(QUESTIONS[3])
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
    journal = load_journal()
    if not journal:
        await update.message.reply_text("Дневник пока пустой.")
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
    entries = get_monthly_gratitude_summary()
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
    entries = get_monthly_gratitude_summary()
    month_name = datetime.now(TIMEZONE).strftime("%B %Y")
    await context.bot.send_message(chat_id=MY_CHAT_ID, text=make_gratitude_summary(entries, month_name), parse_mode="Markdown")


# =====================
# КУРСЫ ВАЛЮТ
# =====================

def get_rates():
    try:
        btc_resp = requests.get("https://api.coingecko.com/api/v3/simple/price", params={"ids": "bitcoin", "vs_currencies": "usd"}, timeout=10)
        btc_usd = btc_resp.json()["bitcoin"]["usd"]
        fx_resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        fx = fx_resp.json()["rates"]
        rub_per_usd = fx["RUB"]
        rub_per_thb = rub_per_usd / fx["THB"]
        return {"btc_usd": btc_usd, "rub_per_usd": rub_per_usd, "rub_per_thb": rub_per_thb}
    except Exception as e:
        logger.error(f"Rates error: {e}")
        return None


def format_rates(rates):
    if not rates:
        return "❌ Не удалось получить курсы."
    now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")
    btc_str = f"{rates['btc_usd']:,.0f}".replace(",", " ")
    return f"📊 *Курсы на {now}*\n\n₿ *Bitcoin:* `${btc_str}`\n💵 *Доллар:* `{rates['rub_per_usd']:.2f} ₽`\n🇹🇭 *Бат:* `{rates['rub_per_thb']:.2f} ₽`\n"


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
# КИНО БОТ
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


async def cinema_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text("Привет! Я слежу за новинками кино 🎬\n\n📅 Каждую субботу в 22:00 — новинки недели\n📅 Первого числа в 20:00 — новинки месяца\n\n/movies — получить подборку прямо сейчас")


async def movies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    try:
        await update.message.reply_text("🎬 Запрашиваю новинки... ⏳")
        await send_movies(context.bot, MY_CHAT_ID, "этой недели")
    except Exception as e:
        logger.error(f"movies_command error: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def weekly_movies(context: ContextTypes.DEFAULT_TYPE):
    await send_movies(context.bot, MY_CHAT_ID, "этой недели")


async def monthly_movies(context: ContextTypes.DEFAULT_TYPE):
    await send_movies(context.bot, MY_CHAT_ID, "этого месяца")


# =====================
# ВИЗОВЫЙ БУДИЛЬНИК
# =====================

def load_visa():
    if not os.path.exists(VISA_FILE):
        return None
    with open(VISA_FILE, "r") as f:
        return json.load(f)


def save_visa(entry_date, expiry_date):
    entry = datetime.strptime(entry_date, "%d.%m.%Y")
    expiry = datetime.strptime(expiry_date, "%d.%m.%Y")
    days = (expiry - entry).days
    data = {"entry_date": entry_date, "expiry_date": expiry_date, "days": days}
    with open(VISA_FILE, "w") as f:
        json.dump(data, f)
    return data


def days_left(expiry_date_str):
    expiry = datetime.strptime(expiry_date_str, "%d.%m.%Y")
    today = datetime.now(TIMEZONE).replace(tzinfo=None)
    return (expiry - today).days


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
            "✅ Дата въезда принята.\n\nТеперь введи дату окончания штампа в формате ДД.ММ.ГГГГ\nНапример: `14.06.2026`",
            parse_mode="Markdown"
        )
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
            f"✅ *Виза сохранена!*\n\n"
            f"📅 Въезд: {entry_date}\n"
            f"🔴 Истекает: *{text}*\n"
            f"⏳ Срок: {visa['days']} дней\n"
            f"📊 Осталось: *{left} дн.*\n\n"
            f"Буду напоминать за 14, 7, 3 и 1 день до окончания.",
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
        f"{emoji} *Статус визы*\n\n"
        f"📅 Въезд: {visa['entry_date']}\n"
        f"🔴 Истекает: {visa['expiry_date']}\n"
        f"⏳ {status_text}\n\n"
        f"`[{bar}]` {pct}% использовано",
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
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=msgs[left] + f"\n\n📅 Истекает: {visa['expiry_date']}",
            parse_mode="Markdown"
        )
    elif left < 0:
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=f"🚨 *ВИЗА ПРОСРОЧЕНА!*\n\nПросрочка: {abs(left)} дней.",
            parse_mode="Markdown"
        )



# =====================
# TODOIST INBOX
# =====================

TODOIST_API = "https://api.todoist.com/api/v1"


def add_task(text):
    resp = requests.post(
        f"{TODOIST_API}/tasks",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
        json={"content": text},
        timeout=10,
    )
    logger.error(f"Todoist add_task: {resp.status_code} {resp.text}")
    return resp.status_code == 200


def get_today_tasks():
    resp = requests.get(
        f"{TODOIST_API}/tasks",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
        params={"filter": "today | overdue"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return []


def format_tasks(tasks):
    if not tasks:
        return "✅ На сегодня задач нет!"
    text = f"📋 *Задачи на сегодня ({len(tasks)}):*\n\n"
    for i, task in enumerate(tasks, 1):
        priority_emoji = {1: "", 2: "🔵", 3: "🟡", 4: "🔴"}.get(task.get("priority", 1), "")
        text += f"{i}. {priority_emoji} {task['content']}\n"
    return text


async def todoist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "Привет! Я твой Todoist-помощник 📋\n\n"
        "Просто напиши мне задачу — я добавлю её в Inbox.\n\n"
        "/tasks — задачи на сегодня\n"
        "/inbox — что в Inbox"
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    tasks = get_today_tasks()
    await update.message.reply_text(format_tasks(tasks), parse_mode="Markdown")


async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    resp = requests.get(
        f"{TODOIST_API}/tasks",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"},
        params={"filter": "#Inbox"},
        timeout=10,
    )
    tasks = resp.json() if resp.status_code == 200 else []
    if not tasks:
        await update.message.reply_text("📥 Inbox пуст!")
        return
    text = f"📥 *Inbox ({len(tasks)}):*\n\n"
    for i, task in enumerate(tasks[:20], 1):
        text += f"{i}. {task['content']}\n"
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
    logger.error(f"Todoist response: {resp.status_code} {resp.text}")
    if resp.status_code == 200:
        await update.message.reply_text(f"✅ Добавлено в Inbox:\n_{text}_", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Ошибка {resp.status_code}: {resp.text[:200]}")


async def morning_tasks(context: ContextTypes.DEFAULT_TYPE):
    tasks = get_today_tasks()
    text = "☀️ *Доброе утро!*\n\n" + format_tasks(tasks)
    await context.bot.send_message(chat_id=MY_CHAT_ID, text=text, parse_mode="Markdown")





# =====================
# ТРЕКЕР НАКОПЛЕНИЙ
# =====================

SAVINGS_FILE = "savings.json"
SAVINGS_GOAL = 10000

MOTIVATIONS = [
    "Каждый доллар приближает тебя к цели. Так держать! 💪",
    "Дисциплина сегодня — свобода завтра. Ты молодец! 🔥",
    "Маленькие шаги ведут к большим результатам. Продолжай! 🚀",
    "Ты уже ближе к цели, чем вчера. Не останавливайся! ⚡",
    "Богатство строится по кирпичику. Ты кладёшь свой! 🏆",
]


def load_savings():
    if not os.path.exists(SAVINGS_FILE):
        return {"balance": 0}
    with open(SAVINGS_FILE, "r") as f:
        return json.load(f)


def save_savings(balance):
    with open(SAVINGS_FILE, "w") as f:
        json.dump({"balance": balance}, f)


def format_progress(balance, goal=SAVINGS_GOAL):
    pct = min(100, int(balance / goal * 100))
    filled = int(pct / 5)
    bar = "█" * filled + "░" * (20 - filled)
    remaining = max(0, goal - balance)
    return (
        "💰 *Накопления*\n\n"
        f"`[{bar}]`\n"
        f"📊 {pct}% выполнено\n"
        f"💵 Накоплено: `{balance:.2f} USDT`\n"
        f"🎯 Цель: `{goal} USDT`\n"
        f"⏳ Осталось: `{remaining:.2f} USDT`"
    )


async def savings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    data = load_savings()
    text = "💰 *Трекер накоплений*\n\nКоманды:\n/balance — текущий баланс\n\nПополнение: напиши `+100`\nСписание: напиши `-50`\n\n"
    text += format_progress(data["balance"])
    await update.message.reply_text(text, parse_mode="Markdown")


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    data = load_savings()
    await update.message.reply_text(format_progress(data["balance"]), parse_mode="Markdown")


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
    data = load_savings()
    old_balance = data["balance"]
    new_balance = old_balance + amount
    if new_balance < 0:
        await update.message.reply_text("❌ Баланс не может быть отрицательным.")
        return
    save_savings(new_balance)
    if old_balance < SAVINGS_GOAL and new_balance >= SAVINGS_GOAL:
        msg = (
            "🎉🏆 *ЦЕЛЬ ДОСТИГНУТА!* 🏆🎉\n\n"
            f"Ты накопил `{new_balance:.2f} USDT` из `{SAVINGS_GOAL} USDT`!\n\n"
            "Это невероятно! Ты доказал себе, что дисциплина и терпение работают. Ты заслужил это! 🚀💪"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    import random
    motivation = random.choice(MOTIVATIONS)
    action = "Пополнено" if amount > 0 else "Списано"
    emoji = "✅" if amount > 0 else "📤"
    msg = f"{emoji} {action} `{abs(amount):.2f} USDT`\n\n" + format_progress(new_balance) + f"\n\n_{motivation}_"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def weekly_savings_report(context: ContextTypes.DEFAULT_TYPE):
    import random
    data = load_savings()
    motivation = random.choice(MOTIVATIONS)
    text = "📅 *Еженедельный отчёт по накоплениям*\n\n" + format_progress(data["balance"]) + f"\n\n_{motivation}_"
    await context.bot.send_message(chat_id=MY_CHAT_ID, text=text, parse_mode="Markdown")


# =====================
# ЗАПУСК
# =====================

async def main():
    # Бот саморефлексии
    reflection_app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q2)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_plan_review)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    reflection_app.add_handler(CommandHandler("start", start_reflection))
    reflection_app.add_handler(conv_handler)
    reflection_app.add_handler(CommandHandler("history", history))
    reflection_app.add_handler(CommandHandler("gratitude", gratitude_summary))
    reflection_app.add_handler(CommandHandler("plan", plan_command))
    reflection_app.job_queue.run_daily(morning_reminder, time=dtime(hour=10, minute=0, tzinfo=TIMEZONE))
    reflection_app.job_queue.run_daily(evening_questions, time=dtime(hour=21, minute=0, tzinfo=TIMEZONE))
    reflection_app.job_queue.run_monthly(monthly_gratitude_report, when=dtime(hour=9, tzinfo=TIMEZONE), day=1)

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

    # Бот накоплений
    savings_app = Application.builder().token(SAVINGS_BOT_TOKEN).build()
    savings_app.add_handler(CommandHandler("start", savings_start))
    savings_app.add_handler(CommandHandler("balance", balance_command))
    savings_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, savings_handle_message))
    savings_app.job_queue.run_daily(
        weekly_savings_report,
        time=dtime(hour=20, minute=0, tzinfo=TIMEZONE),
        days=(6,),
    )

    async with reflection_app, rates_app, cinema_app, visa_app, todoist_app, savings_app:
        await reflection_app.start()
        await rates_app.start()
        await cinema_app.start()
        await visa_app.start()
        await todoist_app.start()
        await savings_app.start()
        await reflection_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await rates_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await cinema_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await visa_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await todoist_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await savings_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Все боты запущены.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
