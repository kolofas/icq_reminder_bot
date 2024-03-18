from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from table import CronModel
from main import send_message, TOKEN

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def process_crons(session: AsyncSession):
    """
    Функция, обрабатывающая активные кроны в базе данных
    :param session: Сессия базы данных SQLAlchemy
    :return:
    """
    current_time = datetime.now()
    crons = await get_active_crons(session, current_time)

    for cron in crons:
        await send_message(cron.user_id, f"Напоминание: {cron.user_message}")


async def get_active_crons(session: AsyncSession, current_time):
    """
    Функция, возвращающая активные кроны, которые должны быть выполнены в текущий момент времени.

    :param session: Сессия базы данных
    :param current_time: Текущее время
    :return: Список активных кронов
    """
    stmt = select(CronModel).where(
        and_(
            CronModel.active == True,
            CronModel.next_execution <= current_time
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


