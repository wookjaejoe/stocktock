from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import *

import sqlalchemy
from sqlalchemy import Column, String

from config import config
from .common import AbstractDynamicTable, StringEnum


class Market(Enum):
    KOSPI = 0
    KOSDAQ = 1


@dataclass
class Stock:
    code: str
    name: str
    market: Market
    industry: Optional[str]
    since: Optional[date]


url = config.database.get_url('bases')
engine = sqlalchemy.create_engine(url, client_encoding='utf-8')


class StockTable(AbstractDynamicTable[Stock]):

    def __init__(self):
        columns = [
            Column('code', String, primary_key=True),
            Column('name', String, nullable=False),
            Column('market', StringEnum(Market), nullable=False)
        ]

        super().__init__(engine, Stock, 'stocks', columns)

    def find(self, code: str) -> Stock:
        return self.query().filter_by(code=code).first()


def all_stocks() -> List[Stock]:
    with StockTable() as stock_table:
        return stock_table.all()
