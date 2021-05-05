from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import *

import sqlalchemy
from sqlalchemy import and_, Column, Integer, Date

from config import config
from .common import Candle
from ..common import AbstractDynamicTable


@dataclass
class DayCandle(Candle):
    pass


url = config.database.get_url('day_candles')
engine = sqlalchemy.create_engine(url, client_encoding='utf-8')


class DayCandleTable(AbstractDynamicTable[DayCandle]):

    def __init__(self, code):
        columns = [Column('date', Date, primary_key=True),
                   Column('open', Integer, nullable=False),
                   Column('close', Integer, nullable=False),
                   Column('low', Integer, nullable=False),
                   Column('high', Integer, nullable=False),
                   Column('vol', Integer, nullable=False)]

        super().__init__(engine, DayCandle, code, columns)

    def find_by_date(self, d: date) -> Optional[DayCandle]:
        return self.query().filter_by(date=d).first()

    def find_all_by_term(self, begin: date, end: date) -> List[DayCandle]:
        assert end >= begin, 'The end must be later than the begin, or equals'
        return self.query().filter(
            and_(
                begin <= self.proxy.date,
                self.proxy.date <= end
            )
        ).all()
