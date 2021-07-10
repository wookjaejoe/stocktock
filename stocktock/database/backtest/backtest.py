# noinspection SpellCheckingInspection
from __future__ import annotations

__author__ = 'wookjae.jo'

import json
import logging
import os
import pickle
from datetime import timedelta, date

import jsons

import database.charts
import database.metrics
import database.stocks
from common.virtual_account import VirtualAccount, NotEnoughDepositException
import abc
from dataclasses import dataclass
from datetime import datetime, time
from typing import *
from common.model import CandlesGroupByCode
from krx import is_business_day


@dataclass
class BacktestEvent:
    when: datetime
    code: str
    price: float
    quantity: int
    comment: str


class BuyEvent(BacktestEvent):
    pass


@dataclass
class SellEvent(BacktestEvent):
    revenue_percent: float


@dataclass
class Model:
    value: int


@dataclass
class DailyLog:
    date: date
    deposit: int  # 예수금
    holding_eval: int  # 보유 종목 평가금액
    holding_count: int  # 보유 종목 개수
    comment: str  # 추가 정보


# noinspection PyMethodMayBeStatic
class AbcBacktest(abc.ABC):

    def __init__(
            self,
            begin: date,
            end: date,
            initial_deposit: int,
    ):
        self.begin = begin
        self.end = end
        self.initial_deposit = initial_deposit
        self.account = VirtualAccount(initial_deposit)

        self.events: List[BacktestEvent] = []
        self.daily_logs: List[DailyLog] = []

        self.start_time: Optional[datetime] = None
        self.finish_time: Optional[datetime] = None

    def _try_buy(
            self,
            when: datetime,
            code: str,
            price: float,
            amount: float,
            comment: str = ''
    ):
        try:
            quantity = int(amount / price)
            self.account.buy(code=code, quantity=quantity, price=price)

            event = BuyEvent(
                when=when, code=code,
                price=price, quantity=quantity,
                comment=comment
            )

            self.events.append(event)
            logging.info(event)
        except NotEnoughDepositException:
            pass

    def _try_sell(
            self,
            when: datetime,
            code: str,
            price: float,
            amount_rate: float = 1,
            comment: str = ''
    ):
        if self.account.has(code):
            bought_price = self.account.get(code).avg_price
            sell_quantity = self.account.sell(code=code, price=price, amount_percent=amount_rate)

            event = SellEvent(
                when=when, code=code,
                price=price, quantity=sell_quantity, revenue_percent=(price - bought_price) / bought_price * 100,
                comment=comment
            )

            self.events.append(event)
            logging.info(event)

    @abc.abstractmethod
    def run(self, d: date):
        pass

    def _evaluate(self, d: date):
        with database.charts.DayCandlesTable() as day_candles_table:
            day_candles = day_candles_table.find_all_at(codes=list(self.account.holdings.keys()), at=d)

        def find_day_candle(code: str):
            for dc in day_candles:
                if dc.code == code:
                    return dc

        holding_eval = 0
        absents = []
        for holding in self.account.holdings.values():
            day_candle = find_day_candle(holding.code)
            if day_candle:
                holding_eval += day_candle.close * holding.quantity
            else:
                holding_eval += holding.total()
                absents.append(holding.code)

        return DailyLog(
            date=d,
            deposit=self.account.deposit,
            holding_count=len(self.account.holdings),
            holding_eval=holding_eval,
            comment=f'Absents: {absents}'
        )

    def start(self):
        self.start_time = datetime.now()
        for d in [self.begin + timedelta(days=i) for i in range((self.end - self.begin).days + 1)]:
            if not is_business_day(d):
                continue

            logging.info(f'Backtest at {d}')
            self.run(d)
            self.daily_logs.append(self._evaluate(d))

        # 백테스트 종료 모든 보유 종목 매도
        with database.charts.DayCandlesTable() as day_candles_table:
            day_candles = day_candles_table.find_all_in(
                codes=list(self.account.holdings.keys()),
                begin=self.end - timedelta(days=20), end=self.end
            )

            day_candles_by_code = CandlesGroupByCode(day_candles)

            for code in self.account.holdings.copy():
                last = day_candles_by_code.get(code)[-1]
                self._try_sell(
                    when=datetime.combine(last.date, time(15, 30)),
                    code=code,
                    price=last.close,
                    comment='백테스트 종료'
                )

        self.finish_time = datetime.now()
        logging.info(f'FINISHED: took {(self.finish_time - self.start_time).seconds} seconds.')

    def dump(self, target_dir) -> str:
        os.makedirs(target_dir, exist_ok=True)

        logging.info('Dumping result...')
        json_path = os.path.join(target_dir, 'backtest.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(jsons.dump(self), f)

        pickle_path = os.path.join(target_dir, 'backtest.pickle')
        with open(pickle_path, 'wb') as f:
            pickle.dump(self, f)

        return target_dir
