
import asyncio

from sqlalchemy import select, and_
from db import async_session
from datetime import datetime
from table import CronModel
import logging

logging.basicConfig(filename="sending_cron.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.addFilter(logging.Filter(__name__))

cron_jobs = {}


async def get_user_id_from_database():
    try:
        async with async_session() as session:
            stmt = select(CronModel.user_id).where(CronModel.active == True).limit(1)
            result = await session.execute(stmt)
            user_id = result.scalar()
            return user_id
    except Exception as e:
        logger.error(f"Error in get_user_id_from_database: {e}")
        return None


async def get_active_crons(session, current_time, user_id):
    try:

        stmt = select(CronModel).where(
            and_(
                CronModel.user_id == user_id,
                CronModel.active == True,
            )
        )
        result = await session.execute(stmt)
        all_crons = result.scalars().all()

        for cron in all_crons:
            cron.next_execution = cron.calculate_next_execution()

        if not all_crons:
            logger.info("No active cron jobs found")
        else:
            logger.info(f"Active cron jobs found: {all_crons}")

        await session.commit()
        return all_crons

    except Exception as e:
        logger.info(f"Error in get_active_crons: {e}")
        return []


async def job(cron_info):
    from main import send_message
    logger.info(f"Job is executed for reminder_id {cron_info['cron_obj'].reminder_id}")
    try:
        await send_message(chat_id=cron_info['cron_obj'].user_id, text=f"Проверка: {cron_info['cron_obj'].user_message}")
        logger.info('Message sent successfully')
        # После успешной отправки удаляем крон из очереди

        del cron_info["cron_obj"]
    except Exception as e:
        logger.error(f"Error sending message: {e}")


async def update_cron_next_execution(session, current_time, user_id):
    try:
        active_crons = await get_active_crons(session, current_time, user_id)

        for cron in active_crons:
            try:
                next_execution = cron.calculate_next_execution()
                cron.next_execution = next_execution
                logger.info(f"Updated cron {cron.cron_expression}: active={cron.active}, next_exec={cron.next_execution}")
            except AttributeError as e:
                logger.error(f"Error getting next execution for cron_expr {cron.cron_expression}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error updating cron next execution: {e}")


async def test_calculate_next_execution():
    try:
        user_id = await get_user_id_from_database()
        async with async_session() as session:
            active_crons = await get_active_crons(session, datetime.now(), user_id)

        for cron in active_crons:
            next_execution = cron.calculate_next_execution()
            logger.info(f"Next execution for cron expression {cron.cron_expression}: {next_execution}")

    except Exception as e:
        logger.error(f"Error in test_calculate_next_exec: {e}")


async def main_logic(cron):
    global cron_jobs
    try:
        cron_key = (cron.user_id, cron.cron_expression)

        if cron_key not in cron_jobs:
            try:
                cron_jobs[cron_key] = {
                    'cron_obj': cron,
                    'user_id': cron.user_id,
                    'user_message': cron.user_message
                }
                logger.info(f"Added cron job to cron_jobs: {cron_key}")
            except Exception as e:
                logger.error(f"Error creating aiocron.crontab for cron_expr {cron.cron_expression}: {e}")
        else:
            logger.info(f"Cron job {cron_key} already in cron_jobs")
            cron_jobs[cron_key]['cron_obj'] = cron
            cron_jobs[cron_key]['user_id'] = cron.user_id
            cron_jobs[cron_key]['user_message'] = cron.user_message
        current_time_main_logic = datetime.now()
        logger.info(f"Current time: {current_time_main_logic}")

        logger.debug(f"Current time: {current_time_main_logic}, Next execution: {cron.cron_expression}")

        if cron.active and cron.next_execution >= current_time_main_logic:
            await job(cron_jobs[cron_key])
            logger.info(f"Job executed for cron_expr {cron.cron_expression}")
        else:
            logger.info("Message not sent. Reason: Next execution time not reached yet")

    except Exception as e:
        logger.error(f"Error in main_logic: {e}")


async def main():
    global cron_jobs

    try:
        while True:
            current_time_main = datetime.now()
            user_id = await get_user_id_from_database()
            async with async_session() as session:
                await update_cron_next_execution(session, current_time_main, user_id)
                active_crons = await get_active_crons(session, current_time_main, user_id)

            for cron in active_crons:
                try:
                    await main_logic(cron)
                except Exception as e:
                    logger.error(f"Error in main_logic: {e}")

            await asyncio.sleep(60)

    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(test_calculate_next_execution())
    loop.create_task(main())
    loop.run_forever()


