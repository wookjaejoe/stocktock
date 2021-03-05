from __future__ import annotations

from datetime import datetime
from typing import *

import sqlalchemy
from sqlalchemy import Column, String, Date, Integer, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import config

engine = sqlalchemy.create_engine(
    f'{config.database.scheme}{config.database.user}:{config.database.pw}@{config.database.host}:{config.database.port}/hermes',
    client_encoding='utf-8')
conn = engine.connect()
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()


def commit():
    session.commit()


class Query:
    @classmethod
    def query(cls) -> sqlalchemy.orm.Query:
        return session.query(cls)

    @classmethod
    def exists(cls, **kwargs):
        return session.query(
            cls.query().filter_by(**kwargs).exists()
        ).scalar()

    def update(self, **kwargs):
        changed = False
        for k, v in kwargs.items():
            if self.__getattribute__(k) != v:
                self.__setattr__(k, v)
                changed = True

        if changed:
            commit()

    def insert(self, do_commit: bool = True):
        session.add(self)


class Stock(Base, Query):
    __tablename__ = 'stocks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    code = Column(String)
    name = Column(String)

    def __str__(self):
        return f'[{self.id}]{self.code}:{self.name}'

    @classmethod
    def find_by_code(cls, code: str) -> Optional[Stock]:
        return cls.query().filter_by(code=code).one_or_none()

    @classmethod
    def get_code(cls, ident):
        return cls.query().get(ident).code


class Candle(Query):
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer)
    date = Column(Date)
    time = Column(Time)
    open = Column(Integer)
    close = Column(Integer)
    low = Column(Integer)
    high = Column(Integer)

    def __str__(self):
        return f'[{self.id}]{self.stock_id}:{self.close}'

    @classmethod
    def insert_many(cls, candles: List[Candle]):
        session.add_all(candles)
        session.commit()


class DayCandle(Candle, Base):
    __tablename__ = 'day_charts'


class MinuteCandle(Candle, Base):
    __tablename__ = 'minute_charts'

    def insert(self, do_commit: bool = False):
        raise Exception(f'Do not call {self.__class__.__name__}:{self.insert.__name__}')


def normalize(code: str):
    return code[-6:]


def print_log(msg: str):
    print(f'[{datetime.now()}] ' + msg)
