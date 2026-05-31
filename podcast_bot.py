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

PODCAST_BOT_TOKEN = os.environ.get("PODCAST_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Темы для поиска подкастов
TOPICS = [
    "саморазвитие подкаст",
    "тренировки мышцы фитнес подкаст",
    "БАДы добавки здоровье подкаст",
    "новинки книг саморазвитие",
    "разбор книги саморазвитие",
    "кофе подкаст",
    "инвестиции подкаст",
    "акции фондовый рынок подкаст",
    "облигации инвестиции подкаст",
    "криптовалюта подкаст",
    "Samsung девайсы обзор",
    "работа в ресторане подкаст",
    "ресторанный маркетинг",
    "управляющий рестораном подкаст",
    "Joe Rogan podcast",
    "параллельные вселенные физика подкаст",
]


# =====================
# SUPABASE
# =====================

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def get_sent_video_ids() -> set:
    """Все ID уже отправленных видео."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/podcast_sent",
            headers=sb_headers(),
            params={"select": "video_id"},
            timeout=10,
        )
        if resp.ok:
            return {row["video_id"] for row in resp.json()}
    except Exception as e:
        logger.error(f"Supabase get sent error: {e}")
    return set()


def mark_video_sent(video_id: str, topic: str):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/podcast_sent",
            headers={**sb_headers(), "Prefer": "resolution=merge-duplicates"},
            json={
                "video_id": video_id,
                "topic": topic,
                "sent_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
            },
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Supabase mark sent error: {e}")


# =====================
# YOUTUBE
# =====================

def search_youtube(topic: str, sent_ids: set) -> dict | None:
    """
    Ищет самое релевантное видео с большим числом просмотров,
    которое ещё не отправлялось.
    """
    try:
        # 1. Поиск релевантных видео по теме
        search_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": YOUTUBE_API_KEY,
                "q": topic,
                "part": "snippet",
                "type": "video",
                "maxResults": 15,
                "order": "relevance",
                "relevanceLanguage": "ru",
                "videoDuration": "long",  # подкасты обычно длинные
            },
            timeout=15,
        )
        items = search_resp.json().get("items", [])
        if not items:
            return None

        # Кандидаты, которые ещё не слали
        candidate_ids = [
            item["id"]["videoId"]
            for item in items
            if item["id"].get("videoId") and item["id"]["videoId"] not in sent_ids
        ]
        if not candidate_ids:
            return None

        # 2. Берём статистику просмотров для кандидатов
        stats_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "key": YOUTUBE_API_KEY,
                "id": ",".join(candidate_ids[:15]),
                "part": "snippet,statistics",
            },
            timeout=15,
        )
        videos = stats_resp.json().get("items", [])
        if not videos:
            return None

        # 3. Сортируем по просмотрам и берём топ
        def views(v):
            return int(v.get("statistics", {}).get("viewCount", 0))

        videos.sort(key=views, reverse=True)
        best = videos[0]

        snippet = best["snippet"]
        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url", "")
        )
        return {
            "video_id": best["id"],
            "title": snippet.get("title", "—"),
            "channel": snippet.get("channelTitle", "—"),
            "thumbnail": thumb,
            "views": views(best),
            "url": f"https://www.youtube.com/watch?v={best['id']}",
        }
    except Exception as e:
        logger.error(f"YouTube search error for '{topic}': {e}")
        return None


def format_caption(topic: str, video: dict) -> str:
    # Убираем служебные слова из темы для красивого заголовка
    clean_topic = topic.replace(" подкаст", "").replace(" обзор", "").strip()
    views_str = f"{video['views']:,}".replace(",", " ")
    return (
        f"🎙 *{clean_topic.capitalize()}*\n\n"
        f"*{video['title']}*\n"
        f"📺 {video['channel']}\n"
        f"👁 {views_str} просмотров\n"
        f"🔗 {video['url']}"
    )


# =====================
# РАССЫЛКА
# =====================

async def send_digest(bot, chat_id: int):
    await bot.send_message(
        chat_id=chat_id,
        text="🎙 *Подкаст-дайджест недели*\n\nСобираю свежие выпуски по твоим темам...",
        parse_mode="Markdown",
    )

    sent_ids = get_sent_video_ids()
    found_count = 0

    for topic in TOPICS:
        video = search_youtube(topic, sent_ids)
        if not video:
            continue
        # Добавляем в локальный набор, чтобы не повторить в этой же рассылке
        sent_ids.add(video["video_id"])
        caption = format_caption(topic, video)
        try:
            if video.get("thumbnail"):
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=video["thumbnail"],
                    caption=caption,
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
            mark_video_sent(video["video_id"], topic)
            found_count += 1
        except Exception as e:
            logger.error(f"Send podcast error ({topic}): {e}")
            try:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
                mark_video_sent(video["video_id"], topic)
                found_count += 1
            except Exception:
                pass
        await asyncio.sleep(0.8)

    if found_count == 0:
        await bot.send_message(chat_id=chat_id, text="😔 Не удалось найти новые видео. Попробуй позже.")
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Готово! Нашёл {found_count} свежих выпусков.",
        )


# =====================
# ХЕНДЛЕРЫ
# =====================

async def podcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "🎙 *Подкаст-бот*\n\n"
        "Каждое воскресенье в 21:00 — свежие подкасты по твоим темам.\n"
        "Видео не повторяются.\n\n"
        "/digest — собрать подборку прямо сейчас",
        parse_mode="Markdown",
    )


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await send_digest(context.bot, MY_CHAT_ID)


# =====================
# ПЛАНИРОВЩИК
# =====================

async def weekly_digest(context: ContextTypes.DEFAULT_TYPE):
    """Воскресенье 21:00."""
    await send_digest(context.bot, MY_CHAT_ID)


# =====================
# ЗАПУСК
# =====================

async def main() -> list:
    """Возвращает список Application для запуска."""
    app = Application.builder().token(PODCAST_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", podcast_start))
    app.add_handler(CommandHandler("digest", digest_command))
    app.job_queue.run_daily(
        weekly_digest,
        time=dtime(hour=21, minute=0, tzinfo=TIMEZONE),
        days=(6,),
    )
    return [app]


async def _run_standalone():
    apps = await main()
    app = apps[0]
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("🎙 Подкаст-бот запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_run_standalone())
