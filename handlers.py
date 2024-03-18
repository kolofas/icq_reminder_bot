import re
from datetime import datetime

import croniter

from db import create_user, get_user_by_chat_id, create_cron, \
    remove_cron, async_session, create_reminder, remove_reminder
from crons import create_annual_cron, create_weekday_cron, create_monthly_cron, create_custom_days_cron, \
    create_quarterly_cron
import logging

logging.basicConfig(filename="handlers.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.addFilter(logging.Filter(__name__))


async def handle_help(chat_id):
    from main import send_message

    try:
        response_text = ("Как пользоваться ботом:\n"
                         "1. /reg - регистрация в системе.\n"
                         "2. /start - получить приветственное сообщение и список команд\n"
                         "3. /remind &lt;дата в формате YYYY-MM-DD&gt; &lt;время в формате HH:MM&gt; &lt;название&gt; \n"
                         "4. /list_reminders - Получить список всех ваших напоминаний.\n"
                         "5. /remove_reminder &lt;номер&gt; - Удалить напоминание по номеру.\n"
                         "6. /add_cron &lt;тип&gt; &lt;параметры&gt; - Добавить периодический крон. Примеры:\n"
                         "       - /add_cron annual &lt;месяц&gt; &lt;день месяца&gt; 12:00\n"
                         "       - /add_cron monthly &lt;день месяца&gt; 14:30\n"
                         "       - /add_cron quarterly &lt;месяц&gt; &lt;день месяца&gt; 10:00\n"
                         "       - /add_cron weekday &lt;день недели&gt; 16:45\n"
                         "       - /add_cron custom_days 1,3,5 08:00\n"
                         "   7. /list_crons - Получить список всех ваших периодических кронов.\n"
                         "   8. /remove_cron &lt;номер&gt; - Удалить периодический крон по номеру.\n"
                         "   9. /helpme - Получить это сообщение с инструкциями.\n")

        await send_message(chat_id, response_text)
        print(f'Пользователю отправлена инструкция на команду /helpme')
    except Exception as e:
        print(f"Error handling /helpme: {e}")


async def handle_start(chat_id, user_id, first_name, nick):
    from main import send_message
    response_text = "Привет! Я icq-reminder бот. Ниже будет меню с командами"
    await send_message(chat_id, response_text)
    print(f"Sent response to user {user_id}: {response_text}")


async def handle_registration(chat_id, user_id, username):
    from main import send_message

    # Используем переменную user с предварительным присвоением значения None
    user = None

    try:
        async with async_session() as session:
            # Попытка получить пользователя из базы данных
            user = await get_user_by_chat_id(chat_id, session)
    except Exception as e:
        print(f'Error during user retrieval: {e}')

    print(f"User retrieved for chat_id {chat_id}: {user}")

    if user and user.chat_id == chat_id:
        # Если пользователь уже зарегистрирован, отправляем сообщение и завершаем функцию
        response_text = "Вы уже зарегистрированы в базе данных"
        await send_message(chat_id, response_text)
        print(f"Sent response to user {user_id}: {response_text}")
        return False
    else:
        try:
            # Попытка зарегистрировать пользователя в базе данных
            async with async_session() as session:
                success = await create_user(chat_id, user_id, username, session)
        except Exception as e:
            print(f"Error during registration: {e}")
            success = False

        response_text = "Вы успешно зарегистрированы в базе данных" if success else "Ошибка при регистрации"

    # Отправка ответного сообщения
    await send_message(chat_id, response_text)
    print(f"Sent response to user {user_id}: {response_text}")

    return success


async def handle_remind(chat_id, user_id, message_text):
    from main import send_message

    # Разбираем команду и извлекаем параметры
    # Например, /remind 2024-02-01 10:00 Meeting with client
    command_parts = message_text.split(' ', 3)  # Увеличиваем количество элементов, чтобы правильно извлекать параметры
    if len(command_parts) == 4 and command_parts[0].lower() == '/remind':
        _, date_str, time_str, reminder_text = command_parts
        try:
            # Проверяем, что строка имеет корректный формат даты и времени
            original_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            formatted_date = original_date.strftime("%d-%m-%Y %H:%M")

            # Создаем напоминание в базе данных
            async with async_session() as session:
                success = await create_reminder(chat_id, user_id, reminder_text, f"{date_str} {time_str}", session)
            if success:
                print(f"Reminder created for {chat_id} at {date_str} {time_str}: {reminder_text}")

                await send_message(chat_id, text=f"<b>Напоминание установлено</b>\n"
                                                 f"<b>Название</b>: {reminder_text}\n"
                                                 f"<b>Время</b>: {formatted_date}\n")

            else:
                print("Error creating reminder")
                await send_message(chat_id, "Ошибка при создании напоминания.")
        except ValueError as e:
            print(f"Error parsing date and time: {e}")
            await send_message(chat_id, "Ошибка при разборе даты и времени.")
    else:
        print("Invalid /remind command format")
        await send_message(chat_id,
                           "Некорректный формат команды /remind. Пожалуйста, используйте /remind YYYY-MM-DD HH:MM Текст напоминания.")


async def handle_list_reminders(chat_id, user_id):
    from main import send_message
    try:
        async with async_session() as session:
            user = await get_user_by_chat_id(chat_id, user_id, session)
            print('user', user.__dict__)
            if user:
                reminders = user.reminders
                if reminders:
                    response_text = "Список ваших напоминаний:\n"
                    for reminder in reminders:
                        response_text += f"{reminder.id}. {reminder.date_time} - {reminder.title}\n"
                else:
                    response_text = "У вас нет напоминаний."
            else:
                response_text = "Пользователь не найден в базе данных."

            # Отправка ответного сообщения
            await send_message(chat_id, response_text)
            print(f"Sent response to user {user_id}: {response_text}")

    except Exception as e:
        print(f"Error in handle_list_reminders: {e}")


async def handle_remove_reminder(chat_id, user_id, message_text):
    from main import send_message
    try:
        parts = message_text.split()
        if len(parts) == 2:
            reminder_id = int(parts[1])

            async with async_session() as session:
                success = await remove_reminder(chat_id, user_id, reminder_id, session)

                if success:
                    response_text = f"Напоминание с номером {reminder_id} успешно удалено"
                else:
                    response_text = f"Не удалось найти напоминание с номером {reminder_id}"

        else:
            response_text = "Некорректный формат команды. Используйте /remove_reminder <номер>"

        await send_message(chat_id, response_text)
        print(f"Отправлен ответ пользователю {user_id}: {response_text}")

    except Exception as e:
        print(f"Error in handle_remove_reminder: {e}")


async def handle_message(event_data):
    from main import send_message
    try:
        print(f"Handling message event: {event_data}")

        chat_info = event_data.get('payload', {}).get('chat', {})
        chat_id = chat_info.get('chatId')

        from_info = event_data.get('payload', {}).get('from', {})
        user_id = from_info.get('userId', 'Unknown User')
        first_name = from_info.get('firstName', 'Unknown First Name')
        nick = from_info.get('nick', 'Unknown Nickname')
        message_text = event_data.get('payload', {}).get('text')

        print(
            f"Received message in chat {chat_id} from user {user_id}, name: {first_name}, nickname: {nick}, message: {message_text}")

        if message_text is not None:
            print(f"Received message in chat {chat_id} from user {user_id}: {message_text}")

            if message_text.lower() == '/reg':
                registration_success = await handle_registration(chat_id, user_id, first_name)
                if registration_success:
                    print("Регистрация успешна")
                else:
                    await send_message(chat_id, "Ошибка при регистрации: Возможно, вы уже зарегистрированы")

            elif message_text.lower() == '/start':
                await handle_start(chat_id, user_id, first_name, nick)

            elif message_text.lower() == '/helpme':
                await handle_help(chat_id)

            if message_text.lower() == '/list_reminders':
                await handle_list_reminders(chat_id, user_id)
            elif message_text.lower().startswith('/remove_reminder'):
                await handle_remove_reminder(chat_id, user_id, message_text)
            elif message_text.lower().startswith('/remind'):
                # Обрабатываем команду /remind
                await handle_remind(chat_id, user_id, message_text)


            elif message_text.startswith('/'):
                # Обрабатываем все остальные команды, начинающиеся с '/'
                await handle_message_with_crons(event_data)
        else:
            print(f"Received message without text in chat {chat_id} from user {user_id}")

        print("Full event_data", event_data)

    except Exception as e:
        print(f"Error handling message: {e}")


async def make_human_date_and_time_from_cron_expression(cron_expression):
    iter = croniter.croniter(cron_expression, datetime.now())
    next_datetime = iter.get_next(datetime)

    return next_datetime.strftime("%d-%m-%Y %H:%M:%S")


async def handle_add_cron(user_id, cron_type, chat_id, *args):
    cron_types_mapping = {
        'annual': create_annual_cron,
        'monthly': create_monthly_cron,
        'quarterly': create_quarterly_cron,
        'weekday': create_weekday_cron,
        'custom_days': create_custom_days_cron
    }

    try:
        if cron_type not in cron_types_mapping:
            return "Неправильный тип крона. Поддерживаемые типы: 'annual', monthly, 'quarterly', 'weekday', 'custom_days'"

        # Используется mapping, чтобы получить соответствующую функцию

        args = list(map(str.strip, args[0]))

        if cron_type == 'annual':
            month, day_of_month = args[0], args[1]
            time_match = re.match(r'(\d{1,2}):(\d{1,2})', args[2])
            if not time_match:
                return "Ошибка парсинга времени. Используйте формат HH:MM"
            hour, minute = map(int, time_match.groups())
            user_message = ' '.join(args[3:])
            cron_expression = create_annual_cron(user_message=user_message,
                                                 month=month,
                                                 day_of_month=day_of_month,
                                                 hour=hour,
                                                 minute=minute)

        elif cron_type == 'monthly':
            day_of_month = args[0]
            time_match = re.match(r'(\d{1,2}):(\d{1,2})', args[1])
            if not time_match:
                return "Ошибка парсинга времени. Используйте формат HH:MM"
            hour, minute = map(int, time_match.groups())
            user_message = ' '.join(args[2:])
            cron_expression = create_monthly_cron(user_message=user_message,
                                                  day_of_month=day_of_month,
                                                  hour=hour,
                                                  minute=minute)
        elif cron_type == 'quarterly':
            month, day_of_month = args[0], args[1]
            time_match = re.match(r'(\d{1,2}):(\d{1,2})', args[2])
            if not time_match:
                return "Ошибка парсинга времени. Используйте формат HH:MM"
            hour, minute = map(int, time_match.groups())
            user_message = ' '.join(args[3:])
            cron_expression = create_quarterly_cron(user_message=user_message,
                                                    month=month,
                                                    day_of_month=day_of_month,
                                                    hour=hour,
                                                    minute=minute)
        elif cron_type == 'weekday':
            day_of_week = args[0]
            time_match = re.match(r'(\d{1,2}):(\d{1,2})', args[1])
            if not time_match:
                return "Ошибка парсинга времени. Используйте формат HH:MM"
            hour, minute = map(int, time_match.groups())
            user_message = ' '.join(args[2:])
            cron_expression = create_weekday_cron(user_message=user_message,
                                                  day_of_week=day_of_week,
                                                  hour=hour,
                                                  minute=minute)
        elif cron_type == 'custom_days':
            print(args)
            day_of_week_str = args[0]
            if not all(day.isdigit() for day in day_of_week_str.split(",")):
                return "Ошибка парсинга дней недели. Используйте числа, разделенные запятой"

            time_match = re.match(r'(\d{1,2}):(\d{1,2})', args[1])
            if not time_match:
                return "Ошибка парсинга времени. Используйте формат HH:MM"
            hour, minute = map(int, time_match.groups())
            user_message = ' '.join(args[2:])
            cron_expression = create_custom_days_cron(user_message=user_message,
                                                      days_of_week=day_of_week_str,
                                                      hour=hour,
                                                      minute=minute)

        # Сохранение крона в базе данных
        async with async_session() as session:
            await create_cron(user_id, chat_id, cron_expression, cron_type, user_message, session)

        make_cron_for_user = await make_human_date_and_time_from_cron_expression(cron_expression)

        return (f"Крон успешно добавлен!\n"
                f"<b>Название</b>: {user_message}\n"
                f"<b>Время</b>: {make_cron_for_user}\n")

    except Exception as e:
        return f"Error adding cron: {str(e)}, {user_message}"


async def handle_list_crons(chat_id, user_id):
    from main import send_message
    try:
        async with async_session() as session:
            user = await get_user_by_chat_id(chat_id, user_id, session)
            print('user', user.__dict__)
            if user:
                crons = user.crons
                if crons:
                    response_text = "Список ваших кронов:\n"
                    for cron in crons:
                        response_text += f"{cron.id}. Название: {cron.user_message}, Время отправки: {cron.next_execution}, Владелец: {cron.user_id}\n"
                else:
                    response_text = "У вас нет кронов"
            else:
                response_text = "Пользователь не найден в базе данных"

            await send_message(chat_id, response_text)
            print(f"Отправлен ответ пользователю {user_id}: {response_text}")

    except Exception as e:
        return f"Error removing cron: {str(e)}"


async def handle_message_with_crons(event_data):
    from main import send_message
    chat_info = event_data.get('payload', {}).get('chat', {})
    chat_id = chat_info.get('chatId')

    from_info = event_data.get('payload', {}).get('from', {})
    user_id = from_info.get('userId', 'Unknown User')
    message_text = event_data.get('payload', {}).get('text')

    try:
        if message_text.lower() == '/list_crons':
            response_text = await handle_list_crons(chat_id, user_id)
        elif message_text.lower().startswith('/add_cron'):
            _, cron_type, *args = message_text.split()
            args = list(map(str.strip, args))
            response_text = await handle_add_cron(user_id, cron_type, chat_id, args)
        elif message_text.lower().startswith('/remove_cron'):
            _, cron_id = message_text.split()
            response_text = await handle_remove_cron(chat_id, user_id, message_text)

        await send_message(chat_id, response_text)
        print(f"Отправлен ответ пользователю {user_id}: {response_text}")

    except Exception as e:
        print(f"Error handling message: {e}")


async def handle_remove_cron(chat_id, user_id, message_text):
    from main import send_message
    try:
        parts = message_text.split()
        if len(parts) == 2:
            cron_id = int(parts[1])

            async with async_session() as session:
                success = await remove_cron(chat_id, user_id, cron_id, session)

                if success:
                    response_text = f"Крон с номер {cron_id} успешно удален"
                else:
                    response_text = f"Не удалось найти крон с номером {cron_id}"
        else:
            response_text = "Некорректный формат команды. Используйте remove_cron <номер>"

        await send_message(chat_id, response_text)
        print(f"Отправлен ответ пользователю {user_id}: {response_text}")

    except Exception as e:
        print(f"Error in handle_remove_cron: {e}")
