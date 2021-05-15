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

import logging
import os

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
    earn_rate: float


@dataclass
class Holding:
    bought_event: BacktestEvent


@dataclass
class DailyReport:
    date: date
    deposit: int  # 예수금
    holding_eval: int  # 보유 종목 평가금액
    holding_count: int  # 보유 종목 개수
    appendix: str  # 추가 정보


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


# noinspection PyMethodMayBeStatic
class Backtest:

    def __init__(
            self,
            begin: date,
            end: date,

            initial_deposit: int,

            limit_holding_count: int,
            limit_buy_amount: int,

            earn_line: float,
            stop_line: float,

            tax_percent: float,
            fee_percent: float,
    ):
        self.strategy = Over5MaStrategy(earn_line, stop_line)
        self.begin = begin
        self.end = end

        self.limit_holding_count = limit_holding_count
        self.limit_buy_amount = limit_buy_amount

        self.earn_line = earn_line
        self.stop_line = stop_line

        self.tax_percent = tax_percent
        self.fee_percent = fee_percent

        self.initial_deposit = initial_deposit
        self.deposit = initial_deposit
        self.events: List[BacktestEvent] = []
        self.holdings: Dict[str, Holding] = {}
        self.daily_reports: List[DailyReport] = []

        self.start_time: Optional[datetime] = None
        self.finish_time: Optional[datetime] = None

    def try_buy(self, when: datetime, code: str, price: int, description: str):
        assert code not in self.holdings

        count = int(self.limit_buy_amount / price)
        if price * count > self.deposit:
            return

        event = BacktestEvent(
            type=BacktestEventType.BUY,
            when=when, code=code, price=price, count=count,
            description=description
        )
        self.events.append(event)
        self.holdings.update({code: Holding(bought_event=event)})
        self.deposit -= price * count

    def try_sell(self, code: str, when: datetime, price: int, description: str):
        assert code in self.holdings
        count = self.holdings.get(code).bought_event.count
        event = BacktestEvent(
            type=BacktestEventType.SELL,
            when=when, code=code, price=price, count=count,
            description=description
        )
        self.events.append(event)
        del self.holdings[code]
        self.deposit += price * count

    def run(self, d: date):
        logging.info(f'The day is {date_to_str(d)}')

        day_candles_map = {}
        with database.charts.DayCandlesTable() as day_candles_table:  # todo: 중복 조회 없이 성능 튜닝
            if not day_candles_table.exists(date=d):
                logging.info(f'Not a business day.')
                return

            logging.info('Fetching day candles...')
            for day_candle in day_candles_table.find_all(
                    codes=[stock.code for stock in stocks],
                    begin=d - timedelta(days=200),
                    end=d
            ):
                if day_candle.code not in day_candles_map:
                    day_candles_map.update({day_candle.code: []})

                day_candles_map.get(day_candle.code).append(day_candle)

        logging.info('Making whitelist...')
        whitelist = []
        for stock in [stock for stock in stocks if stock.code in day_candles_map]:
            day_candles = day_candles_map.get(stock.code)
            ma_calc = MaCalculator([candle.close for candle in day_candles])

            try:
                ma_20_yst = ma_calc.get(20, pos=-1)
                ma_20_yst_2 = ma_calc.get(20, pos=-2)
                ma_60_yst = ma_calc.get(60, pos=-1)
                ma_120_yst = ma_calc.get(120, pos=-1)
            except:
                continue

            # 정배열 and 20MA 기울기 (+) and # !연속음봉
            if ma_20_yst > ma_60_yst > ma_120_yst \
                    and ma_20_yst > ma_20_yst_2 \
                    and len([candle for candle in day_candles[-5:] if candle.open < candle.close]) > 0:
                whitelist.append(stock.code)

        logging.info(f'Streaming minute candles...')
        with database.charts.MinuteCandlesTable(d) as minute_candles_table:
            minute_candles = minute_candles_table.find_all(codes=whitelist, use_yield=True)

        logging.info(f'Looking details at tbe minute candles for {len(whitelist)} stocks...')
        for minute_candle in minute_candles:
            code = minute_candle.code
            cur_price = minute_candle.close
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
                        description='매수 조건 만족'
                    )
                )

    def evaluate(self, d: date):
        day_candles_map = {}
        with database.charts.DayCandlesTable() as day_candles_table:
            day_candles = day_candles_table.find_all(codes=list(self.holdings.keys()), begin=d, end=d)

        for day_candle in day_candles:
            if day_candle.code not in day_candles_map:
                day_candles_map.update({day_candle.code: []})

            day_candles_map.get(day_candle.code).append(day_candle)

        holding_eval = 0
        no_candle_codes = []
        for code in self.holdings:
            bought_event = self.holdings.get(code).bought_event
            if code in day_candles_map:
                # 종가 * 보유 개수
                holding_eval += day_candles_map.get(code)[-1].close * bought_event.count
            else:
                holding_eval += bought_event.price * bought_event.count
                no_candle_codes.append(code)

        holding_eval_feetax = holding_eval * (self.fee_percent + self.tax_percent) / 100
        return DailyReport(
            date=d,
            deposit=self.deposit,
            holding_count=len(self.holdings),
            holding_eval=holding_eval,
            appendix=f'{len(no_candle_codes)} stocks have no day candle.'
        )

    def start(self):
        self.start_time = datetime.now()
        for d in [self.begin + timedelta(days=i) for i in range((self.end - self.begin).days + 1)]:
            self.run(d)
            self.daily_reports.append(self.evaluate(d))

        self.finish_time = datetime.now()
        logging.info(f'FINISHED: took {(self.finish_time - self.start_time).seconds} seconds.')

    def save_report(self):
        target_dir = os.path.join('reports', datetime.now().strftime('%Y%m%d_%H%M%S'))
        os.makedirs(target_dir, exist_ok=True)

        # 요약(입력, 최종 평가)
        write_csv(
            path=os.path.join(target_dir, 'summary.csv'),
            headers=[
                '시작일', '종료일', '구동 시간(sec)',
                '최초 예수금', '최종 예수금',
                '수익금', '수익율(%)',
                '익절라인(%)', '손절라인(%)', '매매 수수료(%)', '매도 세금(%)',
            ],
            values=[[
                self.begin, self.end, (self.finish_time - self.start_time).seconds,
                self.initial_deposit, self.deposit,
                self.deposit - self.initial_deposit, self.deposit - self.initial_deposit / self.initial_deposit,
                self.earn_line, self.stop_line, self.fee_percent, self.tax_percent,
            ]]
        )

        # 일별 평가
        write_csv(
            path=os.path.join(target_dir, 'daily_report.csv'),
            headers=[
                '날짜',
                '예수금', '보유 종목 평가금액', '총 평가금액',
                '비고'
            ],
            values=[[
                dr.date,
                dr.deposit, dr.holding_eval, dr.deposit + dr.holding_eval,
                dr.appendix
            ] for dr in self.daily_reports]
        )

        # 주문 목록
        write_csv(
            path=os.path.join(target_dir, 'events.csv'),
            headers=[
                '일시', '구분', '종목코드', '종목명', '가격',
                '수량', '주문총액', '비고',
                '수익율(%)'
            ],
            values=[[
                event.when, event.type.name, event.code, get_name(event.code), event.price,
                event.count, event.price * event.count, event.description,
                event.earn_rate if isinstance(event, BacktestSellEvent) else ''
            ] for event in self.events]
        )


import csv


def write_csv(path: str, headers: List[Any], values: List[List[Any]]):
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(values)
