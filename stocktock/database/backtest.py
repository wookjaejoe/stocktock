from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from multiprocessing.pool import ThreadPool
from typing import *

import database.charts
from .metrics import MaCalculator


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
    earn_rate: float


@dataclass
class Holding:
    bought_at: datetime
    bought_price: int
    bought_count: int


# noinspection PyMethodMayBeStatic
class Backtest:

    def __init__(self,
                 codes: List[str],
                 begin: date,
                 end: date,
                 limit_holding_count: int,
                 limit_buy_amount: int,
                 earn_line: float,
                 stop_line: float):

        self.codes = codes
        self.begin = begin
        self.end = end
        self.limit_holding_count = limit_holding_count
        self.limit_buy_amount = limit_buy_amount
        self.earn_line = earn_line
        self.stop_line = stop_line
        self.events: List[BacktestEvent] = []
        self.holdings: Dict[str, Holding] = {}

    def try_order(self, code: str, when: datetime, type_: BacktestEventType, price: int, count: int, description: str):
        if type_ == BacktestEventType.BUY:
            if code in self.holdings:
                return
            else:
                self.events.append(
                    BacktestEvent(
                        when=when,
                        code=code,
                        type=type_,
                        price=price,
                        count=count,
                        description=description
                    )
                )
                self.holdings.update({code: Holding(
                    bought_at=when,
                    bought_price=price,
                    bought_count=count
                )})

        elif type_ == BacktestEventType.SELL:
            if code in self.holdings:
                bought_price = self.holdings.get(code).bought_price
                self.events.append(
                    BacktestSellEvent(
                        when=when,
                        code=code,
                        type=type_,
                        price=price,
                        count=count,
                        description=description,
                        earn_rate=(price - bought_price) / bought_price
                    )
                )
                del self.holdings[code]
            else:
                return

    def start(self):
        days = [self.begin + timedelta(days=x) for x in range(1000) if self.begin + timedelta(days=x) <= self.end]
        for d in days:
            self.on_date(d)

        return self.events

    # noinspection DuplicatedCode
    def on_date(self, d: date):
        with database.charts.DayCandlesTable() as day_table:
            day_candles = day_table.find_all(begin=self.begin - timedelta(days=365), end=d)

        day_candles.sort(key=lambda candle: candle.date)

        ma_calc_map = {}
        for code in self.codes:
            ma_calc_map.update({code: MaCalculator([candle for candle in day_candles if candle.code == code])})

        # Make whitelist with
        white_list = []
        for code in self.codes:
            ma_calc: MaCalculator = ma_calc_map.get(code)
            ma_5_yst, ma_20_yst = ma_calc.get(5, pos=-1), ma_calc.get(20, pos=-1)
            ma_60_yst, ma_120_yst = ma_calc.get(60, pos=-1), ma_calc.get(120, pos=-1)
            day_candle_at = [candle for candle in ma_calc.candles if candle.date == d]
            if not day_candle_at:
                continue
            day_candle = day_candle_at[0]

            if code in self.holdings:  # 보유중
                if day_candle.low <= self.holdings.get(code).bought_price * self.earn_line <= day_candle.high:
                    white_list.append(code)
                elif day_candle.low <= self.stop_line <= day_candle.high:
                    white_list.append(code)
            else:  # 미보유
                if ma_120_yst < ma_60_yst < ma_5_yst < ma_20_yst \
                        and day_candle.open < ma_5_yst \
                        and day_candle.low <= ma_5_yst <= day_candle.high:
                    white_list.append(code)

        if not white_list:
            return

        # Backtest with minute candles
        with database.charts.MinuteCandlesTable(d) as minute_table:
            minute_candles = minute_table.find_all(codes=white_list)
            minute_candles.sort(key=lambda candle: datetime.combine(candle.date, candle.time))

        if not minute_candles:
            return

        # ma_60_yst < ma_5_yst < ma_20_yst and detail.open < ma_5_yst <= detail.bought_price < ma_5_yst * 1.025:
        for candle in minute_candles:
            ma_calc: MaCalculator = ma_calc_map.get(candle.code)
            ma_5_yst, ma_20_yst = ma_calc.get(5, pos=-1), ma_calc.get(20, pos=-1)
            ma_60_yst, ma_120_yst = ma_calc.get(60, pos=-1), ma_calc.get(120, pos=-1)
            day_candle_at = [candle for candle in ma_calc.candles if candle.date == d]
            day_candle = day_candle_at[0]

            # ma_60_yst < ma_5_yst < ma_20_yst and open < ma_5_yst <= price < ma_5_yst * 1.025
            if candle.code in self.holdings:  # 보유중
                if candle.price >= self.earn_line * candle.close:
                    self.try_order(
                        candle.code, datetime.combine(candle.date, candle.time), BacktestEventType.SELL,
                        price=candle.price, count=self.holdings.get(candle.code).bought_count,
                        description=f'{(self.earn_line - 1) * 100}% 익절'
                    )
                elif candle.price <= self.stop_line * candle.close:
                    self.try_order(
                        candle.code, datetime.combine(candle.date, candle.time), BacktestEventType.SELL,
                        price=candle.price, count=self.holdings.get(candle.code).bought_count,
                        description=f'{(self.stop_line - 1) * 100}%손절'
                    )
            else:  # 미보유
                if ma_60_yst < ma_5_yst < ma_20_yst and day_candle.open < ma_5_yst <= candle.price < ma_5_yst * 1.025 \
                        and day_candle.open < ma_5_yst <= candle.price <= ma_5_yst * 1.025:
                    self.try_order(
                        candle.code, datetime.combine(candle.date, candle.time), BacktestEventType.BUY,
                        price=candle.price, count=int(self.limit_buy_amount / candle.price),
                        description=f'매수 조건 만족'
                    )
