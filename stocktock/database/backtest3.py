from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
from enum import Enum
from typing import *

import database.charts
import database.metrics
import database.stocks
from common.metric import MaCalculator
from strategy.strategies import Over5MaStrategy

with database.stocks.StockTable() as stock_table:
    stocks = stock_table.all()


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
    earn_rate: float


@dataclass
class Holding:
    bought_event: BacktestEvent


# noinspection PyMethodMayBeStatic
class Backtest:

    def __init__(
            self,
            begin: date,
            end: date,
            limit_holding_count: int,
            limit_buy_amount: int,
            earn_line: float,
            stop_line: float
    ):
        self.begin = begin
        self.end = end
        self.limit_holding_count = limit_holding_count
        self.limit_buy_amount = limit_buy_amount
        self.earn_line = earn_line
        self.stop_line = stop_line

        self.strategy = Over5MaStrategy(earn_line, stop_line)
        self.events: List[BacktestEvent] = []
        self.holdings: Dict[str, Holding] = {}

    def try_order(self,
                  event_type: BacktestEventType,
                  when: datetime,
                  code: str,
                  price: int,
                  count: int,
                  description: str):
        event = BacktestEvent(
            type=event_type, when=when, code=code, price=price, count=int(self.limit_buy_amount / price),
            description=description
        )

        self.events.append(event)
        return event

    def try_buy(self, when: datetime, code: str, price: int, description: str):
        assert code not in self.holdings
        event = self.try_order(
            event_type=BacktestEventType.BUY,
            when=when,
            code=code,
            price=price,
            count=int(self.limit_buy_amount / price),
            description=description
        )
        self.holdings.update({code: Holding(bought_event=event)})

    def try_sell(self, code: str, when: datetime, price: int, description: str):
        assert code in self.holdings
        self.try_order(
            event_type=BacktestEventType.BUY,
            when=when,
            code=code,
            price=price,
            count=self.holdings.get(code).bought_event.count,
            description=description
        )
        del self.holdings[code]

    def run(self, d: date):
        print('Collecting day candles...')

        day_candles_map = {}
        with database.charts.DayCandlesTable() as day_candles_table:  # todo: 중복 조회 없이 성능 튜닝
            if not day_candles_table.exists(date=d):
                return

            for day_candle in day_candles_table.find_all(begin=d - timedelta(days=200), end=d):
                if day_candle.code not in day_candles_map:
                    day_candles_map.update({day_candle.code: []})

                day_candles_map.get(day_candle.code).append(day_candle)

        whitelist = []
        for stock in stocks:
            ma_calc = MaCalculator(day_candles_map.get(stock.code))

            try:
                ma_20_yst = ma_calc.get(5, pos=-1)
                ma_60_yst = ma_calc.get(60, pos=-1)
                ma_120_yst = ma_calc.get(120, pos=-1)
            except:
                continue

            # todo: 다른 조건들 추가해서 whitelist 축소
            if ma_20_yst > ma_60_yst > ma_120_yst:
                whitelist.append(stock.code)

        with database.charts.MinuteCandlesTable(d) as minute_candles_table:
            minute_candles = minute_candles_table.find_all(codes=whitelist, use_yield=True)
            for minute_candle in minute_candles:
                code = minute_candle.code
                cur_price = minute_candle.price
                when = datetime.combine(minute_candle.date, minute_candle.time)

                if minute_candle.code in self.holdings.keys():  # 보유중
                    buy_price = self.holdings.get(minute_candle.code).bought_event.price
                    margin_percent = (cur_price - buy_price) / buy_price * 100
                    if margin_percent >= self.earn_line:
                        self.try_sell(code=code, when=when, price=cur_price, description='익절')
                    elif margin_percent <= self.stop_line:
                        self.try_sell(code=code, when=when, price=cur_price, description='손절')

                    self.strategy.check_and_sell()
                else:  # 미보유
                    self.strategy.check_and_buy(
                        day_candles=day_candles_map.get(minute_candle.code),
                        cur_price=minute_candle.close,
                        buy=lambda: self.try_buy(
                            code=code,
                            when=when,
                            price=cur_price,
                            description=''
                        )
                    )

    def start(self):
        for d in [self.begin + timedelta(days=i) for i in range((self.end - self.begin).days + 1)]:
            self.run(d)
