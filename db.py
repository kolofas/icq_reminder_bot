import logging
import uuid
import sys
import os

from crontab import CronTab
from sqlalchemy import create_engine, select, exc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '/home/nikita/PycharmProjects/pythonProject1/icq_bot/table.py')))

from table import User, Base, SingleReminder, CronModel
from datetime import datetime
from typing import Optional

DATABASE_URL = 'postgresql+asyncpg://kolofas:okoko@localhost/icqdatabase'

async_engine = create_async_engine(DATABASE_URL, echo=True, future=True)
sync_engine = create_engine(DATABASE_URL, echo=True)
metadata = Base.metadata

Session = sessionmaker(bind=sync_engine)
async_session = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession, autocommit=False)


async def connect_db():
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_session()
    except Exception as e:
        print(f"Error in connect_db: {e}")
        return None


async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_user(chat_id, user_id, username, session):
    try:
        await connect_db()
        user = User(chat_id=chat_id, user_id=user_id, username=username)
        session.add(user)
        await session.commit()
        return True
    except IntegrityError as e:
        # Обработка случая, когда пользователь с таким chat_id уже существует
        print(f"IntegrityError in create_user: {e}")
        await session.rollback()
        return False
    except Exception as e:
        # Обработка других ошибок
        print(f"Error in create_user: {e}")
        await session.rollback()
        return False


async def get_user_by_chat_id(chat_id, user_id, session) -> Optional[User]:
    print(f"Поиск пользователя с chat_id: {user_id}, {chat_id}")
    try:
        stmt = select(User).options(joinedload(User.reminders), joinedload(User.crons)).where(User.user_id == user_id)
        print(f'stmt - {stmt}')
        result = await session.execute(stmt)
        user = result.scalar()
        print(f"Получен пользователь с chat_id и user_id: {chat_id} {user_id}")
        return user
    except exc.SQLAlchemyError as e:
        print(f"Ошибка в get_user_by_chat_id: {e}")
        return None


async def create_reminder(chat_id, user_id, title, date_time_str, session):
    try:
        date_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
        reminder = SingleReminder(chat_id=chat_id, user_id=user_id, title=title, date_time=date_time)
        session.add(reminder)
        await session.commit()
        return True
    except Exception as e:
        print(f"Error in create_reminder: {e}")
        await session.rollback()
        return False


async def remove_reminder(chat_id, user_id, reminder_id, session: AsyncSession):
    try:
        user = await get_user_by_chat_id(chat_id, session)

        if user:
            stmt = select(SingleReminder).filter_by(id=reminder_id, user=user)
            result = await session.execute(stmt)
            reminder = result.scalar()

            if reminder:
                await session.delete(reminder)
                await session.commit()
                return True

    except SQLAlchemyError as e:
        print(f"Ошбика в remove_reminder: {e}")
        await session.rollback()

    return False


async def create_cron(user_id, chat_id, cron_expression, cron_type, user_message, session: AsyncSession):
    try:
        print(f"User ID: {user_id}, Cron Expression: {cron_expression}")
        cron = CronModel(user_id=user_id, chat_id=chat_id, cron_expression=cron_expression, cron_type=cron_type,
                         user_message=user_message)
        session.add(cron)
        await session.commit()
        return True
    except Exception as e:
        print(f"Error adding cron: {str(e)}")
        await session.rollback()
        return False


async def remove_cron(chat_id, user_id, cron_id, session):
    try:
        user = await get_user_by_chat_id(chat_id, user_id, session)
        print(f"user - {user}")

        if user:
            stmt = select(CronModel).filter_by(id=cron_id, user=user)
            result = await session.execute(stmt)
            cron = result.scalar()

            if cron:
                user_cron = CronTab(user='root')
                user_cron.remove_all(command=cron.user_message)
                user_cron.write()

                await session.delete(cron)
                await session.commit()

                return True

    except SQLAlchemyError as e:
        print(f"Ошибка в remove_cron: {e}")
        await session.rollback()

    return False
