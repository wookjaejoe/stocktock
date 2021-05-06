from dataclasses import dataclass
from datetime import date
from typing import *
from multiprocessing.pool import ThreadPool

@dataclass
class Candle:
    date: date
    open: int
    close: int
    low: int
    high: int
    vol: int




class CandleFetcher:

    def __init__(self, table_class):
        self.table_class = table_class
        self.result = []

    def get(self, codes: List[str], begin: date, end: date):
        def _get(code: str):
            with self.table_class(code) as day_candle_table:
                return day_candle_table.find_all_by_term(begin, end)

        with ThreadPool(5) as pool:
            return pool.map(_get, codes)
