import os
import logging
import requests
from datetime import datetime, time as dtime
import pytz
import asyncio

from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes

TIMEZONE = pytz.timezone("Asia/Bangkok")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("CINEMA_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")
KP_API_KEY = os.environ.get("KP_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"


def get_new_movies(limit=8):
    """Получаем новинки кино из TMDB."""
    try:
        resp = requests.get(
            f"{TMDB_BASE}/movie/now_playing",
            params={
                "api_key": TMDB_API_KEY,
                "language": "ru-RU",
                "region": "US",
                "page": 1,
            },
            timeout=10,
        )
        movies = resp.json().get("results", [])[:limit]
        return movies
    except Exception as e:
        logger.error(f"TMDB error: {e}")
        return []


def get_movie_details(tmdb_id):
    """Детали фильма из TMDB — жанры, актёры."""
    try:
        detail = requests.get(
            f"{TMDB_BASE}/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "ru-RU"},
            timeout=10,
        ).json()

        credits = requests.get(
            f"{TMDB_BASE}/movie/{tmdb_id}/credits",
            params={"api_key": TMDB_API_KEY, "language": "ru-RU"},
            timeout=10,
        ).json()

        cast = credits.get("cast", [])[:3]
        actors = ", ".join(a["name"] for a in cast) if cast else "—"
        genres = ", ".join(g["name"] for g in detail.get("genres", [])[:3]) or "—"
        overview = detail.get("overview", "")
        if len(overview) > 150:
            overview = overview[:150] + "..."

        return {
            "genres": genres,
            "actors": actors,
            "overview": overview,
            "imdb_id": detail.get("imdb_id", ""),
        }
    except Exception as e:
        logger.error(f"TMDB details error: {e}")
        return {"genres": "—", "actors": "—", "overview": "—", "imdb_id": ""}


def get_omdb_ratings(imdb_id, title):
    """Рейтинги из OMDB — IMDb и Rotten Tomatoes."""
    if not imdb_id and not title:
        return {}
    try:
        params = {"apikey": OMDB_API_KEY}
        if imdb_id:
            params["i"] = imdb_id
        else:
            params["t"] = title

        resp = requests.get("https://www.omdbapi.com/", params=params, timeout=10)
        data = resp.json()

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
    """Рейтинг с Кинопоиска."""
    try:
        params = {"query": title, "limit": 1}
        if year:
            params["year"] = year

        resp = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie/search",
            headers={"X-API-KEY": KP_API_KEY},
            params=params,
            timeout=10,
        )
        data = resp.json()
        docs = data.get("docs", [])
        if docs:
            rating = docs[0].get("rating", {})
            kp = rating.get("kp")
            if kp and kp > 0:
                return f"{kp:.1f}"
    except Exception as e:
        logger.error(f"KP error: {e}")
    return None


def format_movie_caption(movie, details, omdb, kp_rating):
    """Формируем подпись к постеру фильма."""
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
    """Отправляем подборку новинок."""
    await bot.send_message(
        chat_id=chat_id,
        text=f"🎬 *Новинки кино {period_label}*\n\nСобираю данные...",
        parse_mode="Markdown"
    )

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
                poster_url = f"{TMDB_IMG}{poster_path}"
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=poster_url,
                    caption=caption,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="Markdown"
                )

            await asyncio.sleep(1)  # небольшая пауза между фильмами

        except Exception as e:
            logger.error(f"Error sending movie: {e}")
            continue


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "Привет! Я слежу за новинками кино 🎬\n\n"
        "📅 Каждую субботу в 22:00 — новинки недели\n"
        "📅 Первого числа в 20:00 — новинки месяца\n\n"
        "/movies — получить подборку прямо сейчас"
    )


async def movies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await send_movies(update.get_bot(), MY_CHAT_ID, "этой недели")


async def weekly_movies(context: ContextTypes.DEFAULT_TYPE):
    """Еженедельная рассылка по субботам в 22:00."""
    await send_movies(context.bot, MY_CHAT_ID, "этой недели")


async def monthly_movies(context: ContextTypes.DEFAULT_TYPE):
    """Ежемесячная рассылка 1-го числа в 20:00."""
    await send_movies(context.bot, MY_CHAT_ID, "этого месяца")


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("movies", movies_command))

    # Каждую субботу в 22:00
    app.job_queue.run_daily(
        weekly_movies,
        time=dtime(hour=22, minute=0, second=0, tzinfo=TIMEZONE),
        days=(5,),  # 5 = суббота
    )

    # Первого числа каждого месяца в 20:00
    app.job_queue.run_monthly(
        monthly_movies,
        when=dtime(hour=20, minute=0, second=0, tzinfo=TIMEZONE),
        day=1,
    )

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Кино бот запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
