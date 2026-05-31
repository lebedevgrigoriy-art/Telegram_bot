import os
import logging
import requests
import asyncio
from datetime import datetime, time as dtime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

TIMEZONE = pytz.timezone("Asia/Bangkok")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

WISHLIST_BOT_TOKEN = os.environ.get("WISHLIST_BOT_TOKEN")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID"))
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


# =====================
# КОНВЕРТАЦИЯ ВАЛЮТ
# =====================

def get_thb_rub_rates():
    """Возвращает (rub_per_thb, thb_per_rub) по текущему курсу. None при ошибке."""
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        rates = resp.json()["rates"]
        rub = rates["RUB"]
        thb = rates["THB"]
        rub_per_thb = rub / thb   # сколько рублей за 1 бат
        thb_per_rub = thb / rub   # сколько батов за 1 рубль
        return rub_per_thb, thb_per_rub
    except Exception as e:
        logger.error(f"Currency rates error: {e}")
        return None, None


def detect_currency(price_str: str) -> str | None:
    """Определяет валюту по строке цены. Возвращает 'THB', 'RUB' или None."""
    s = price_str.lower()
    if "฿" in price_str or "бат" in s or "thb" in s:
        return "THB"
    if "₽" in price_str or "руб" in s or "rub" in s:
        return "RUB"
    return None


def extract_amount(price_str: str) -> float | None:
    """Вытаскивает число из строки цены."""
    digits = "".join(c for c in price_str if c.isdigit() or c == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def build_price_with_conversion(price_str: str) -> str:
    """
    Берёт исходную цену, добавляет конвертацию в другую валюту.
    '5000 ฿' -> '5000 ฿ (≈ 13 200 ₽)'
    """
    if not price_str:
        return ""
    currency = detect_currency(price_str)
    amount = extract_amount(price_str)
    if not currency or not amount:
        return price_str  # не смогли распознать — оставляем как есть

    rub_per_thb, thb_per_rub = get_thb_rub_rates()
    if not rub_per_thb:
        return price_str  # курс недоступен — оставляем как есть

    if currency == "THB":
        converted = amount * rub_per_thb
        conv_str = f"{converted:,.0f}".replace(",", " ")
        return f"{amount:,.0f} ฿".replace(",", " ") + f" (≈ {conv_str} ₽)"
    else:  # RUB
        converted = amount * thb_per_rub
        conv_str = f"{converted:,.0f}".replace(",", " ")
        return f"{amount:,.0f} ₽".replace(",", " ") + f" (≈ {conv_str} ฿)"


# =====================
# SUPABASE
# =====================

def sb_headers(extra_prefer=""):
    prefer = "return=representation"
    if extra_prefer:
        prefer = extra_prefer + "," + prefer
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def add_wish(title, price, photo_id):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/wishlist",
            headers=sb_headers(),
            json={
                "title": title,
                "price": price,
                "photo_id": photo_id,
                "bought": False,
                "created_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
            },
            timeout=10,
        )
        return True
    except Exception as e:
        logger.error(f"add_wish error: {e}")
        return False


def get_wishes(bought=False):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/wishlist",
            headers=sb_headers(),
            params={"bought": f"eq.{str(bought).lower()}", "order": "created_at.desc"},
            timeout=10,
        )
        return resp.json() if resp.ok else []
    except Exception as e:
        logger.error(f"get_wishes error: {e}")
        return []


def mark_bought(wish_id):
    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/wishlist",
            headers=sb_headers(),
            params={"id": f"eq.{wish_id}"},
            json={"bought": True, "bought_at": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M")},
            timeout=10,
        )
        return True
    except Exception as e:
        logger.error(f"mark_bought error: {e}")
        return False


# =====================
# ПАРСИНГ ЦЕНЫ ИЗ ТЕКСТА
# =====================

def split_title_price(text: str):
    """
    Разделяет 'Наушники Sony 25000 ₽' на название и цену.
    Цена — последнее число (возможно с символом валюты).
    """
    text = text.strip()
    parts = text.split()
    price_tokens = []
    # Идём с конца, собираем токены похожие на цену/валюту
    while parts:
        last = parts[-1]
        cleaned = last.replace("₽", "").replace("฿", "").replace("руб", "").replace("бат", "").replace(",", "").replace(".", "")
        if cleaned.isdigit() or last in ("₽", "฿", "руб", "бат", "$"):
            price_tokens.insert(0, parts.pop())
        else:
            break
    title = " ".join(parts).strip()
    price = " ".join(price_tokens).strip()
    if not title:  # вся строка оказалась "ценой" — значит цены нет
        title = text
        price = ""
    return title, price


# =====================
# ОТОБРАЖЕНИЕ
# =====================

def wish_caption(wish):
    text = f"🎁 *{wish['title']}*"
    if wish.get("price"):
        text += f"\n💰 {wish['price']}"
    return text


async def show_wishlist(bot, chat_id):
    wishes = get_wishes(bought=False)
    if not wishes:
        await bot.send_message(chat_id=chat_id, text="✨ Вишлист пуст. Добавь желание — пришли мне название и цену (можно с фото).")
        return

    total_count = len(wishes)
    await bot.send_message(
        chat_id=chat_id,
        text=f"🌟 *Твой вишлист* ({total_count})\n\nОтметь купленное кнопкой под желанием.",
        parse_mode="Markdown",
    )

    for wish in wishes:
        caption = wish_caption(wish)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Куплено", callback_data=f"bought:{wish['id']}")
        ]])
        try:
            if wish.get("photo_id"):
                await bot.send_photo(chat_id=chat_id, photo=wish["photo_id"], caption=caption, parse_mode="Markdown", reply_markup=keyboard)
            else:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"show wish error: {e}")
        await asyncio.sleep(0.3)


# =====================
# ХЕНДЛЕРЫ
# =====================

async def wishlist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await update.message.reply_text(
        "🌟 *Вишлист-бот*\n\n"
        "Добавить желание: пришли название и цену.\n"
        "Например: `Наушники Sony 25000 ₽`\n"
        "Можно с фото — отправь фото с подписью.\n\n"
        "/wishlist — показать желания\n"
        "/done — исполненные желания",
        parse_mode="Markdown",
    )


async def wishlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    await show_wishlist(context.bot, MY_CHAT_ID)


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return
    wishes = get_wishes(bought=True)
    if not wishes:
        await update.message.reply_text("Пока нет исполненных желаний. Всё впереди! 💪")
        return
    text = f"🏆 *Исполненные желания* ({len(wishes)}):\n\n"
    for wish in wishes:
        text += f"✅ {wish['title']}"
        if wish.get("price"):
            text += f" — {wish['price']}"
        text += "\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != MY_CHAT_ID:
        return

    # Фото с подписью
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        title, price = split_title_price(caption)
        if not title:
            title = "Без названия"
        price = build_price_with_conversion(price)
        add_wish(title, price, photo_id)
        await update.message.reply_text(f"✅ Добавлено в вишлист:\n🎁 {title}" + (f"\n💰 {price}" if price else ""))
        return

    # Просто текст
    text = (update.message.text or "").strip()
    if not text:
        return
    title, price = split_title_price(text)
    price = build_price_with_conversion(price)
    add_wish(title, price, None)
    await update.message.reply_text(f"✅ Добавлено в вишлист:\n🎁 {title}" + (f"\n💰 {price}" if price else ""))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("bought:"):
        wish_id = query.data.split(":", 1)[1]
        mark_bought(wish_id)
        # Убираем кнопку и помечаем выполненным
        try:
            if query.message.photo:
                await query.edit_message_caption(
                    caption=(query.message.caption or "") + "\n\n✅ *Куплено!*",
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    text=(query.message.text or "") + "\n\n✅ *Куплено!*",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error(f"edit message error: {e}")


# =====================
# ЕЖЕНЕДЕЛЬНОЕ НАПОМИНАНИЕ
# =====================

async def weekly_wishlist(context: ContextTypes.DEFAULT_TYPE):
    """Воскресенье вечером."""
    wishes = get_wishes(bought=False)
    if not wishes:
        await context.bot.send_message(chat_id=MY_CHAT_ID, text="🌟 Вишлист пуст. Может, добавишь новую цель на неделю?")
        return
    await context.bot.send_message(
        chat_id=MY_CHAT_ID,
        text="🌟 *Воскресный обзор вишлиста*\n\nЧто удалось достичь на этой неделе? Отметь купленное 👇",
        parse_mode="Markdown",
    )
    await show_wishlist(context.bot, MY_CHAT_ID)


# =====================
# ЗАПУСК
# =====================

async def main() -> list:
    app = Application.builder().token(WISHLIST_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", wishlist_start))
    app.add_handler(CommandHandler("wishlist", wishlist_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

    # Воскресенье 20:00 (понедельник=0 ... воскресенье=6)
    app.job_queue.run_daily(weekly_wishlist, time=dtime(hour=20, minute=0, tzinfo=TIMEZONE), days=(6,))

    return [app]


async def _run_standalone():
    apps = await main()
    app = apps[0]
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("🌟 Вишлист-бот запущен.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_run_standalone())
