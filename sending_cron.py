import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import select
from db import async_session
from datetime import datetime
from table import CronModel

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('reminder_service.log', maxBytes=1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# Отправка сообщения
async def job(user_id, chat_id, message):
    logger.info(f"Отправка сообщения пользовалю {user_id}: {message}")
    from main import send_message
    await send_message(chat_id=chat_id, text=message)


async def update_next_execution(reminder):
    async with async_session() as session:
        reminder.next_execution = reminder.calculate_next_execution()
        logger.info(f"Следующее время выполнения напоминания {reminder.id}: {reminder.next_execution}")
        session.add(reminder)
        await session.commit()


async def load_reminders_from_database():
    async with async_session() as session:
        stmt = select(CronModel).where(CronModel.active == True)
        result = await session.execute(stmt)
        reminders = result.scalars().all()
        return reminders


# Обработка напоминаний из базы данных
async def process_reminders():
    reminders = await load_reminders_from_database()
    current_time = datetime.now()

    for reminder in reminders:
        logger.info(f"Проверка напоминания {reminder.id}")
        if reminder.next_execution is None:
            reminder.next_execution = reminder.calculate_next_execution()
            async with async_session() as session:
                session.add(reminder)
                await session.commit()

        if reminder.next_execution <= current_time:
            logger.info(f"Отправка напоминанию {reminder.id} пользователю {reminder.user_id}")
            await job(reminder.user_id, reminder.chat_id, reminder.user_message)
            await update_next_execution(reminder)


async def main():
    while True:
        await process_reminders()
        await asyncio.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
