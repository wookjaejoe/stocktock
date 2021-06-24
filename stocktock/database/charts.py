# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from dataclasses import dataclass
from datetime import date, time, datetime
from typing import *

import sqlalchemy
from sqlalchemy import Column, Date, Time, Integer, and_, String

from common.model import Candle
from config import config
from .common import AbstractDynamicTable


@dataclass
class DayCandle(Candle):
    pass


@dataclass
class MinuteCandle(Candle):
    time: time

    def datetime(self):
        return datetime.combine(self.date, self.time)


url = config.database.get_url('charts')
engine = sqlalchemy.create_engine(url, client_encoding='utf-8')


class DayCandlesTable(AbstractDynamicTable[DayCandle]):

    def __init__(self):
        columns = [
            Column('code', String, primary_key=True),
            Column('date', Date, primary_key=True),
            Column('open', Integer, nullable=False),
            Column('close', Integer, nullable=False),
            Column('low', Integer, nullable=False),
            Column('high', Integer, nullable=False),
            Column('vol', Integer, nullable=False)
        ]

        super().__init__(engine, DayCandle, 'day_candles', columns)

    def find_all_in(self,
                    codes: List[str] = None,
                    begin: date = None,
                    end: date = None) -> List[DayCandle]:
        if begin and end:
            assert end >= begin, 'The end must be later than the begin, or equals'

        return self.query().filter(
            and_(
                self.proxy.code.in_(codes) if codes else True,
                begin <= self.proxy.date if begin else True,
                self.proxy.date <= end if end else True,
            )
        ).all()

    def find_all_at(self, codes: List[str], at: date) -> List[DayCandle]:
        return self.query().filter(
            and_(
                self.proxy.code.in_(codes) if codes else True,
                self.proxy.date == at,
            )
        ).all()

    def find(self, code: str, at: date) -> DayCandle:
        return self.query().filter_by(code=code, date=at).first()


class MinuteCandlesTable(AbstractDynamicTable[MinuteCandle]):

    def __init__(
            self,
            d: date,
            create_if_not_exists: bool = False
    ):
        columns = [
            Column('code', String, primary_key=True),
            Column('date', Date, primary_key=True),
            Column('time', Time, primary_key=True),
            Column('open', Integer, nullable=False),
            Column('close', Integer, nullable=False),
            Column('low', Integer, nullable=False),
            Column('high', Integer, nullable=False),
            Column('vol', Integer, nullable=False)
        ]

        super().__init__(
            engine,
            MinuteCandle,
            'minute_candles_' + d.strftime('%Y%m%d'),
            columns,
            create_if_not_exists=create_if_not_exists
        )

    def find_all(self, codes: List[str], use_yield=False) -> List[MinuteCandle]:
        query = self.query().filter(self.proxy.code.in_(codes))
        if use_yield:
            return query.yield_per(count=1000)
        else:
            return query.all()
