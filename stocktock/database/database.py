from __future__ import annotations

from datetime import date, datetime
from typing import *

import sqlalchemy
from sqlalchemy import Column, String, Date, Integer, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import config

engine = sqlalchemy.create_engine(
    f'{config.database_scheme}{config.database_user}:{config.database_pw}@{config.database_host}:{config.database_port}/hermes',
    client_encoding='utf-8')
conn = engine.connect()
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()


class Query:
    @classmethod
    def query(cls) -> sqlalchemy.orm.Query:
        return session.query(cls)

    @classmethod
    def exists(cls, **kwargs):
        return session.query(
            cls.query().filter_by(**kwargs).exists()
        ).scalar()


class Stock(Base, Query):
    __tablename__ = 'stocks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    code = Column(String)
    name = Column(String)

    def __str__(self):
        return f'[{self.id}]{self.code}:{self.name}'

    def insert(self, commit: bool):
        if not self.exists(code=self.code):  # if not exists
            session.add(self)
            if commit:
                session.commit()

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

    def insert(self, commit: bool):
        session.add(self)
        if commit:
            session.commit()

    @classmethod
    def insert_many(cls, candles: List[Candle]):
        session.add_all(candles)
        session.commit()


class DayCandle(Candle, Base):
    __tablename__ = 'day_charts'


class MinuteCandle(Candle, Base):
    __tablename__ = 'minute_charts'


def normalize(code: str):
    return code[-6:]


def print_log(msg: str):
    print(f'[{datetime.now()}] ' + msg)


def update_day_charts(begin: date, end: date):
    from creon import charts, stocks

    def convert(_stock_id, source: charts.ChartData) -> DayCandle:
        # noinspection PyTypeChecker
        return DayCandle(
            stock_id=_stock_id,
            date=source.datetime.date(),
            time=None,
            open=source.open,
            close=source.close,
            low=source.low,
            high=source.high
        )

    all_stocks = Stock.query().all()

    for stock in all_stocks:
        chart = charts.request_by_term(
            code=stocks.find(stock.code).code,
            chart_type=charts.ChartType.DAY,
            begin=begin,
            end=end,
        )

        print_log(f'[{all_stocks.index(stock) + 1}/{len(all_stocks)}] ...')
        stock_id = Stock.find_by_code(normalize(stock.code)).id

        # DayCandle.insert_many([convert(stock_id, candle) for candle in chart])
        session.bulk_save_objects([convert(stock_id, candle) for candle in chart])
        session.commit()


def main():
    # noinspection PyUnresolvedReferences
    session.execute(MinuteCandle.__table__.delete())
    session.commit()


if __name__ == '__main__':
    main()
