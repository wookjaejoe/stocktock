from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, datetime
from typing import *

import sqlalchemy
from sqlalchemy import and_, Column, Integer, Date, Time

from config import config
from .common import Candle
from ..common import AbstractDynamicTable


@dataclass
class MinuteCandle(Candle):
    time: time


url = config.database.get_url('minute_candles')
engine = sqlalchemy.create_engine(url, client_encoding='utf-8')


class MinuteCandleTable(AbstractDynamicTable):

    def __init__(self, code):
        columns = [Column('date', Date, primary_key=True),
                   Column('time', Time, primary_key=True),
                   Column('open', Integer, nullable=False),
                   Column('close', Integer, nullable=False),
                   Column('low', Integer, nullable=False),
                   Column('high', Integer, nullable=False),
                   Column('vol', Integer, nullable=False)]

        super().__init__(engine, MinuteCandle, code, columns)

    def find_by_date(self, d: date) -> List[MinuteCandle]:
        return self.query().filter_by(date=d).all()

    def find_by_datetime(self, d: date, t: time) -> Optional[MinuteCandle]:
        return self.query().filter_by(date=d, time=t).first()

    def find_all_by_term(self, begin: datetime, end: datetime) -> List[MinuteCandle]:
        assert end >= begin, 'The end must be later than the begin, or equals'
        return self.query().filter(
            and_(
                begin.date() <= self.proxy.date,
                self.proxy.date <= end.date(),
                begin.time() <= self.proxy.time,
                self.proxy.time <= end.time()
            )
        ).all()
