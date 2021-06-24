# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import *

import database.charts
import database.metrics
import database.stocks

with database.stocks.StockTable() as stock_table:
    stocks = [stock for stock in stock_table.all() if '스팩' not in stock.name]


def date_to_str(d: date):
    return d.strftime('%Y-%m-%d')


def get_name(code: str):
    for stock in stocks:
        if stock.code == code:
            return stock.name


class BacktestEventType(Enum):
    BUY = 0
    SELL = 1


@dataclass
class BacktestEvent:
    when: datetime
    code: str
    type: BacktestEventType
    price: int
    count: int
    description: str


@dataclass
class BacktestSellEvent(BacktestEvent):
    bought_event: BacktestEvent


@dataclass
class Holding:
    bought_event: BacktestEvent


@dataclass
class DailyLog:
    date: date
    deposit: int  # 예수금
    holding_eval: int  # 보유 종목 평가금액
    holding_count: int  # 보유 종목 개수
    description: str  # 추가 정보


@dataclass
class BacktestReport:
    begin: date  # 시작일
    end: date  # 종료일
    running_time: int  # 구동 시간(초)
    earn_line: float  # 익절라인
    stop_line: float  # 손절라인


class Cache:
    pass


cache = Cache()


class DayCandleFetcher:
    def fetch(self):
        pass


class MinuteCandleFetcher:
    def fetch(self):
        pass


def get_fl_map(codes: List[str], begin: date, end: date):
    with database.charts.DayCandlesTable() as day_candles_table:
        candles = day_candles_table.find_all(codes=codes, begin=begin, end=end)

    candles_by_code = {}
    for candle in candles:
        if candle.code not in candles_by_code:
            candles_by_code.update({candle.code: []})

        candles_by_code.get(candle.code).append(candle)

    return {code: (candles[0].open, candles[-1].close) for code, candles in candles_by_code.items()}
