from dataclasses import dataclass

import sqlalchemy
from sqlalchemy import Column, String

from config import config
from .common import AbstractDynamicTable


@dataclass
class Stock:
    code: str
    name: str


url = config.database.get_url('stocks')
engine = sqlalchemy.create_engine(url, client_encoding='utf-8')


class StockDynamicTable(AbstractDynamicTable[Stock]):

    def __init__(self):
        columns = [
            Column('code', String, primary_key=True),
            Column('name', String, nullable=False),
        ]

        super().__init__(engine, Stock, 'stocks', columns)
