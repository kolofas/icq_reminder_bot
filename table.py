from datetime import datetime
import uuid

import aiocron
from aiocron import crontab
from croniter import croniter
from sqlalchemy import Column, String, DateTime, Integer, select, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(String, primary_key=True)
    chat_id = Column(String)
    username = Column(String, nullable=False)


class SingleReminder(Base):
    __tablename__ = 'single_reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    chat_id = Column(String)
    user = relationship('User', back_populates='reminders')
    title = Column(String, nullable=False)
    date_time = Column(DateTime, nullable=False, default=func.now())


User.reminders = relationship('SingleReminder', order_by=SingleReminder.date_time, back_populates='user', uselist=True,
                              lazy='select')


class CronModel(Base):
    __tablename__ = 'crons'

    id = Column(Integer, primary_key=True)
    reminder_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey('users.user_id'))
    chat_id = Column(String)
    user = relationship('User', back_populates='crons')
    cron_expression = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    cron_type = Column(String)
    user_message = Column(String)
    active = Column(Boolean, default=True)
    next_execution = Column(DateTime)

    def __init__(self, user_id, chat_id, cron_expression, cron_type, user_message):
        self.user_id = user_id
        self.chat_id = chat_id
        self.reminder_id = str(uuid.uuid4())
        self.cron_expression = cron_expression
        self.cron_type = cron_type
        self.user_message = user_message
        self.cron_object = aiocron.crontab(cron_expression)

    def calculate_next_execution(self):
        current_time = datetime.now()
        iter = croniter(self.cron_expression, current_time)
        return iter.get_next(datetime)


User.crons = relationship('CronModel', back_populates='user')