# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from datetime import date
from typing import *

import database.charts
import database.metrics
import database.stocks

with database.stocks.StockTable() as stock_table:
    stocks = [stock for stock in stock_table.all() if '스팩' not in stock.name]


def get_name(code: str):
    for stock in stocks:
        if stock.code == code:
            return stock.name


def get_fl_map(codes: List[str], begin: date, end: date):
    with database.charts.DayCandlesTable() as day_candles_table:
        candles = day_candles_table.find_all_in(codes=codes, begin=begin, end=end)

    candles_by_code = {}
    for candle in candles:
        if candle.code not in candles_by_code:
            candles_by_code.update({candle.code: []})

        candles_by_code.get(candle.code).append(candle)

    return {code: (candles[0].open, candles[-1].close) for code, candles in candles_by_code.items()}
