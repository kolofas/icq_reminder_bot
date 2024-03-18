import datetime
import re

from croniter import croniter
from crontab import CronTab


def create_cron_command(user_message, cron_str):
    cron = CronTab(user='root')
    job = cron.new(command=user_message)
    job.setall(cron_str)
    cron.write()
    return str(cron_str)


def create_weekday_cron(*, day_of_week, hour, minute, user_message):
    cron_str = f'{minute} {hour} * * {day_of_week}'
    return create_cron_command(user_message, cron_str)


def create_custom_days_cron(*, days_of_week, hour, minute, user_message):
    cron_str = f'{minute} {hour} * * {days_of_week}'
    return create_cron_command(user_message, cron_str)


def create_monthly_cron(*, day_of_month, hour, minute, user_message):
    cron_str = f'{minute} {hour} {day_of_month} * *'
    return create_cron_command(user_message, cron_str)


def create_quarterly_cron(*, month, day_of_month, hour, minute, user_message):
    cron_str = f'{minute} {hour} {day_of_month} {month} *'
    return create_cron_command(user_message, cron_str)


def create_annual_cron(*, month, day_of_month, hour, minute, user_message):
    cron_str = f'{minute} {hour} {day_of_month} {month} *'
    return create_cron_command(user_message, cron_str)

