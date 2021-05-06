from dataclasses import dataclass
from datetime import date, time, datetime
from enum import Enum
from typing import *

from database.candles import day, minute
from .metrics import MaCalculator
from multiprocessing.pool import ThreadPool


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
        self.day_charts: Dict[str, List[day.DayCandle]] = {}

    def try_order(self, code: str, when: datetime, type_: BacktestEventType, price: int, count: int, descripttion: str):
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
                        description=descripttion
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
                        description=descripttion,
                        earn_rate=(price - bought_price) / bought_price
                    )
                )
                del self.holdings[code]
            else:
                return

    def start(self):
        self.events = []

        with ThreadPool(5) as pool:
            pool.map(self.test_one, self.codes)

        self.events.sort(key=lambda evt: evt.when)
        return self.events

    def test_one(self, code):
        print('1', end='')
        with day.DayCandleTable(code) as day_candle_table:
            all_day_candles = day_candle_table.all()
            all_day_candles.sort(key=lambda candle: candle.date)
            self.day_charts.update({code: all_day_candles})

        day_candle = None
        for day_candle in [candle for candle in all_day_candles if self.begin <= candle.date <= self.end]:
            candles = [candle for candle in all_day_candles if candle.date <= day_candle.date]
            ma_calc = MaCalculator(candles=candles)
            ma_5_yst = ma_calc.get(5, pos=-1)
            ma_20_yst = ma_calc.get(20, pos=-1)
            ma_60_yst = ma_calc.get(60, pos=-1)
            ma_120_yst = ma_calc.get(120, pos=-1)

            if code in self.holdings:  # 보유중: 매도 시그널 확인
                if day_candle.low <= self.holdings.get(code).bought_price * self.earn_line <= day_candle.high:
                    self.lookup(code, day_candle.date, ma_calc)

                if day_candle.low <= self.stop_line <= day_candle.high:
                    self.lookup(code, day_candle.date, ma_calc)

            else:  # 미보유: 매수 시그널 확인
                if ma_120_yst < ma_60_yst < ma_5_yst < ma_20_yst \
                        and day_candle.open < ma_5_yst \
                        and day_candle.low <= ma_5_yst <= day_candle.high:
                    self.lookup(code, day_candle.date, ma_calc)

        if day_candle:
            close = day_candle.close
            self.try_order(
                code, datetime.combine(day_candle.date, time(15, 30)), BacktestEventType.SELL,
                price=close, count=int(self.limit_buy_amount / close),
                descripttion=f'기간 종료'
            )

    def lookup(self, code: str, dt: date, ma_calc: MaCalculator):
        ma_5_yst = ma_calc.get(5, pos=-1)
        ma_20_yst = ma_calc.get(20, pos=-1)
        ma_60_yst = ma_calc.get(60, pos=-1)
        ma_120_yst = ma_calc.get(120, pos=-1)

        with minute.MinuteCandleTable(code) as minute_candle_table:
            minute_candles = minute_candle_table.find_by_date(dt)
            minute_candles.sort(key=lambda candle: datetime.combine(date=candle.date, time=candle.time))

        for minute_candle in minute_candles:
            close = minute_candle.close
            dt = datetime.combine(minute_candle.date, minute_candle.time)
            if ma_5_yst <= close <= ma_5_yst * 1.025:
                self.try_order(
                    code, dt, BacktestEventType.BUY,
                    price=close, count=int(self.limit_buy_amount / close),
                    descripttion='매수 조건 만족'
                )

            if code in self.holdings:
                bought_price = self.holdings.get(code).bought_price

                if close >= bought_price * self.earn_line:
                    self.try_order(
                        code, dt, BacktestEventType.SELL,
                        price=close, count=int(self.limit_buy_amount / close),
                        descripttion=f'{self.earn_line}% 익절'
                    )
                elif close <= bought_price * self.stop_line:
                    self.try_order(
                        code, dt, BacktestEventType.SELL,
                        price=close, count=int(self.limit_buy_amount / close),
                        descripttion=f'{self.stop_line}% 손절'
                    )
