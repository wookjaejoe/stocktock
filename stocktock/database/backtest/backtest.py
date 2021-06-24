# noinspection SpellCheckingInspection
from __future__ import annotations

__author__ = 'wookjae.jo'

import json
import logging
import os
import pickle
from datetime import timedelta, time

import jsons

import database.charts
import database.metrics
import database.stocks
from common.metric import MaCalculator
from strategy.strategies import Over5MaStrategy
from .common import *


# noinspection PyMethodMayBeStatic
class Backtest:

    def __init__(
            self,
            begin: date,
            end: date,

            initial_deposit: int,

            limit_holding_count: int,
            limit_buy_amount: int,
            limit_holding_days: int,

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
        self.limit_holding_days = limit_holding_days

        self.earn_line = earn_line
        self.stop_line = stop_line

        self.tax_percent = tax_percent
        self.fee_percent = fee_percent

        self.initial_deposit = initial_deposit
        self.deposit = initial_deposit
        self.events: List[BacktestEvent] = []
        self.holdings: Dict[str, Holding] = {}
        self.daily_logs: List[DailyLog] = []

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
        self.deposit -= int(price * count * self.fee_percent / 100)  # 수수료 차감

    def try_sell(self, code: str, when: datetime, price: int, description: str):
        assert code in self.holdings
        count = self.holdings.get(code).bought_event.count
        event = BacktestSellEvent(
            type=BacktestEventType.SELL,
            when=when, code=code, price=price, count=count,
            description=description,
            bought_event=self.holdings.get(code).bought_event
        )
        self.events.append(event)
        del self.holdings[code]
        self.deposit += price * count
        self.deposit -= int(price * count * self.fee_percent / 100)  # 수수료 차감
        self.deposit -= int(price * count * self.tax_percent / 100)  # 매도세 차감

    def run(self, d: date):
        logging.info(f'The day is {date_to_str(d)}')

        day_candles_map = {}
        with database.charts.DayCandlesTable() as day_candles_table:
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
        whitelist = list(self.holdings.keys())
        for stock in [stock for stock in stocks if stock.code in day_candles_map]:
            day_candles = day_candles_map.get(stock.code)
            ma_calc = MaCalculator([candle.close for candle in day_candles])

            try:
                ma_5_yst = ma_calc.get(5, pos=-1)
                ma_20_yst = ma_calc.get(20, pos=-1)
                ma_20_yst_2 = ma_calc.get(20, pos=-2)
                ma_60_yst = ma_calc.get(60, pos=-1)
                ma_120_yst = ma_calc.get(120, pos=-1)
            except:
                continue

            # 배열상태 and 20MA 기울기 (+) and # !연속음봉
            if ma_20_yst > ma_5_yst \
                    and ma_20_yst > ma_60_yst > ma_120_yst \
                    and ma_20_yst > ma_20_yst_2 \
                    and len([candle for candle in day_candles[-5:] if candle.open < candle.close]) > 0:
                whitelist.append(stock.code)

        logging.info(f'Streaming minute candles...')
        with database.charts.MinuteCandlesTable(d) as minute_candles_table:
            minute_candles = minute_candles_table.find_all(codes=whitelist)

        minute_candles.sort(key=lambda candle: candle.time)

        logging.info(f'Looking details at tbe minute candles for {len(whitelist)} stocks...')
        for minute_candle in minute_candles:
            code = minute_candle.code
            cur_price = minute_candle.close
            when = datetime.combine(minute_candle.date, minute_candle.time)

            if code in self.holdings.keys():  # 보유중
                buy_price = self.holdings.get(code).bought_event.price
                margin_percent = (cur_price - buy_price) / buy_price * 100
                day_candles_after_bought = [dc for dc in day_candles_map.get(code) if
                                            dc.date >= self.holdings.get(code).bought_event.when.date()]
                holding_days = len(day_candles_after_bought)
                # 손익절 라인 확인
                if margin_percent >= self.earn_line:
                    self.try_sell(code=code, when=when, price=cur_price, description='익절')
                elif margin_percent <= self.stop_line:
                    self.try_sell(code=code, when=when, price=cur_price, description='손절')
                # 매도 5+ 거래일 지난 15:00 이후
                elif holding_days >= 5 and when.time() > time(14, 30):
                    # 변동성 1% 미만이면, 매도
                    if abs(margin_percent) < 1:
                        self.try_sell(code=code, when=when, price=cur_price, description='미변동')
                    # 보유 기간 제한 20일
                    elif holding_days >= self.limit_holding_days:
                        self.try_sell(code=code, when=when, price=cur_price,
                                      description=f'보유 기간 제한({self.limit_holding_days})일 초과')

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

        holding_eval -= holding_eval * self.tax_percent / 100  # 매도세 반영

        return DailyLog(
            date=d,
            deposit=self.deposit,
            holding_count=len(self.holdings),
            holding_eval=holding_eval,
            description=f'{len(no_candle_codes)} stocks have no day candle.'
        )

    def start(self):
        self.start_time = datetime.now()
        for d in [self.begin + timedelta(days=i) for i in range((self.end - self.begin).days + 1)]:
            self.run(d)
            self.daily_logs.append(self.evaluate(d))

        for holding in self.holdings.copy().values():
            code = holding.bought_event.code
            _, last = get_fl_map([code], self.begin, self.end).get(code)
            self.try_sell(
                code=code,
                when=datetime.combine(self.end, time(15, 30)),
                price=last,
                description='백테스트 종료')

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
