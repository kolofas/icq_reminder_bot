from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db import async_session
from table import SingleReminder
from async_icq.bot import AsyncBot
import datetime
import logging

logging.basicConfig(filename='checker_reminder.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Создание подключения к базе данных
engine = create_engine('postgresql+psycopg2://kolofas:okoko@localhost/icqdatabase')
Session = sessionmaker(bind=engine)


TOKEN = '001.2762277535.2286663239:1011313001'


# Создание экземпляра бота
bot = AsyncBot(token=TOKEN)


# Асинхронная функция для проверки напоминаний
async def date_finish_check():
    async with async_session() as conn:
        date_now = datetime.datetime.now()

        stmt = select(SingleReminder).filter(SingleReminder.date_time <= date_now)
        reminds_to_get_out = (await conn.execute(stmt)).scalars().all()

        # Обработка каждого напоминания
        for remind in reminds_to_get_out:
            try:
                # Отправка сообщения
                await bot.send_text(chatId=remind.chat_id, text=remind.title)
            except Exception as e:
                print(f"Error sending message: {e}")

            # Удаление напоминания из базы данных
            await conn.delete(remind)
        await conn.commit()


# Основная асинхронная функция
async def main():
    while True:
        await date_finish_check()
        await asyncio.sleep(60)


# Точка входа в программу
if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


