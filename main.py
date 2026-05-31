"""
Главный файл запуска. Объединяет все боты в один процесс.
Каждый бот-модуль предоставляет async-функцию main(), возвращающую список Application.
Если один модуль падает при сборке — остальные всё равно стартуют.
"""
import asyncio
import logging

from telegram import Update

import bot as core_bots          # существующие 7 ботов
import podcast_bot               # подкаст-дайджест
import wishlist_bot              # вишлист
import quote_bot                 # цитата дня

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("main")

# Список модулей. Чтобы добавить нового бота — просто допиши сюда его модуль.
MODULES = [
    ("core", core_bots),
    ("podcast", podcast_bot),
    ("wishlist", wishlist_bot),
    ("quote", quote_bot),
]


async def main():
    all_apps = []

    # Собираем приложения из каждого модуля. Падение одного не валит остальные.
    for name, module in MODULES:
        try:
            apps = await module.main()
            all_apps.extend(apps)
            logger.info(f"Модуль '{name}' собран: {len(apps)} ботов.")
        except Exception as e:
            logger.error(f"Модуль '{name}' не запустился: {e}")

    if not all_apps:
        logger.error("Ни один бот не собрался. Выход.")
        return

    # Запускаем все приложения
    for app in all_apps:
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")

    logger.info(f"Запущено ботов: {len(all_apps)}.")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
