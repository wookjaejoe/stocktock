import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta, datetime
from typing import *

sys.path.append(os.path.join(os.path.dirname(__file__), 'stocktock'))

from model import Candle
from utils import calc, log

log.init(logging.DEBUG)
import creon.provider

from creon import charts, stocks

logger = logging.getLogger()

available_codes = stocks.get_availables()
details: Dict[str, stocks.StockDetail2] = {detail.code: detail for detail in stocks.get_details(available_codes)}


@dataclass
class Holding:
    code: str
    count: int
    price: int
    is_5_beneath: bool = False
    is_10_beneath: bool = False
    max_price: int = 0


BUY_LIMIT = 100_0000


class Wallet:

    def __init__(self):
        self.earnings = 0
        self.holdings: List[Holding] = []

    def has(self, code):
        return code in [holding.code for holding in self.holdings]

    def get(self, code):
        for holding in self.holdings:
            if code == holding.code:
                return holding

    def buy(self, dt: datetime, code, count, price):
        total = count * price

        self.holdings.append(Holding(code, count, price))
        tokens = [
            dt,  # 주문시각
            'BUY',  # 구분
            code,  # 종목코드
            stocks.get_name(code),  # 종목명
            details.get(code).capitalization(),
            price,  # 주문가
            count,  # 주문수량
            total,  # 주문총액
            'N/A',  # 수익율
            'N/A',  # 수익금
            count,  # 잔여수량
        ]

        logger.critical(', '.join([str(token) for token in tokens]))

    def amount_to_count(self, code, amount: float):
        return math.ceil(self.get(code).count * amount)

    def sell(self, dt: datetime, code, sell_price, sell_amount: float):
        holding = self.get(code)

        # 매도 수량 계산
        sell_count = math.ceil(holding.count * sell_amount)

        # 보유 수량에서 매도 수량 만큼 차감
        holding.count = holding.count - sell_count
        if holding.count == 0:
            # 전량 매도
            self.holdings.remove(holding)

        earnings = sell_price * sell_count - holding.price * sell_count
        self.earnings += earnings
        tokens = [
            dt,  # 시각
            'SELL',  # 구분
            code,  # 종목코드
            stocks.get_name(code),  # 종목명
            details.get(code).capitalization(),  # 시총
            sell_price,  # 주문가
            sell_count,  # 주문수량
            sell_price * sell_count,  # 주문총액
            calc.earnings_ratio(holding.price, sell_price),  # 수익율
            earnings,  # 수익금
            holding.count,  # 잔여수량
        ]

        logger.critical(', '.join([str(token) for token in tokens]))


class NotEnoughChartException(BaseException):
    def __init__(self, code, name):
        self.code = code
        self.name = name

    def __str__(self):
        return f'Not enough chart for {self.name}({self.code})'


@dataclass
class Event:
    type: str
    datetime: datetime
    price: int
    count: int


@dataclass
class SimulationResult:
    code: str
    name: str
    begin: date
    end: date
    candles: List[Candle] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)


def normalize(code: str):
    return code[-6:]


class Simulator:

    def __init__(self, code: str, begin: date, end: date):
        self.wallet = Wallet()
        self.code = code
        self.result = SimulationResult(code=normalize(self.code), name=stocks.find(code).name, begin=begin, end=end)
        self.candle_provider = creon.provider.MinuteCandleProvdider(code, begin, end)
        self.candle_provider.subscribers.append(self.on_candle)
        self.candle_provider.subscribers.append(lambda candle: self.result.candles.append(candle))
        self.daily_candles: List[Candle] = charts.request_by_term(
            code=code,
            chart_type=charts.ChartType.DAY,
            begin=begin - timedelta(days=200),
            end=end
        )

        if not self.daily_candles:
            raise NotEnoughChartException(code, details.get(code).name)

        self.daily_candles.sort(key=lambda candle: datetime.combine(candle.date, candle.time))

        if not self.daily_candles[0].date < begin < self.daily_candles[-1].date:
            raise NotEnoughChartException(code=code, name=stocks.get_name(code))

        self.daily_candles: Dict[date, Candle] = {candle.date: candle
                                                  for candle in self.daily_candles}
        self.last_candle: Optional[Candle] = None

    def ma(self, dt: date, length: int, cur_price: int = 0, pos: int = 0):
        values = [candle.close for candle in self.daily_candles.values()
                  if candle.date < dt] + [cur_price]

        if pos:
            values = values[-length + pos: pos]
        else:
            values = values[-length:]

        if length > len(values):
            raise NotEnoughChartException(self.code, stocks.get_name(self.code))

        return sum(values) / length

    def _sell(self, dt, price, count):
        self.result.events.append(Event(type='SELL', datetime=dt, price=price, count=count))

    def _buy(self, dt, price, count):
        self.result.events.append(Event(type='BUY', datetime=dt, price=price, count=count))

    def start(self):
        self.candle_provider.start()
        self.on_finished()
        return self.result

    def on_finished(self):
        pass

    def on_candle(self, candle: Candle):
        pass


class BreakAbove5MaEventSimulator(Simulator):

    def __init__(self, code: str, begin: date, end: date, earning_line=7, stop_line=-5):
        super().__init__(stocks.find(code).code, begin, end)
        self.earning_line = earning_line
        self.stop_line = stop_line

    def on_finished(self):
        if self.last_candle and self.wallet.has(self.code):
            self._sell(dt=datetime.combine(self.last_candle.date, self.last_candle.time),
                       price=self.last_candle.close,
                       count=self.wallet.amount_to_count(self.code, 1))
            self.wallet.sell(dt=datetime.combine(self.last_candle.date, self.last_candle.time),
                             code=self.last_candle.code,
                             sell_price=self.last_candle.close,
                             sell_amount=1)

        detail = details.get(self.code)

        if self.wallet.earnings:
            final_msg_items = [
                '###',
                self.code,
                detail.name,
                detail.capitalization(),
                self.wallet.earnings
            ]

            logger.critical(', '.join([str(item) for item in final_msg_items]))

    def on_candle(self, candle: Candle):
        self.last_candle = candle
        ma_5_yst = self.ma(dt=candle.date, pos=-1, length=5)
        ma_20_yst = self.ma(dt=candle.date, pos=-1, length=20)
        ma_60_yst = self.ma(dt=candle.date, pos=-1, length=60)
        ma_120_yst = self.ma(dt=candle.date, pos=-1, length=120)

        cur_price = candle.close
        daily_candle = self.daily_candles.get(candle.date)

        if self.wallet.has(code=self.code):  # 보유 종목에 대한 매도 판단
            holding = self.wallet.get(self.code)

            # max 갱신
            holding.max_price = max(holding.max_price, cur_price)

            # 수익율 계산
            earnings_rate = calc.earnings_ratio(self.wallet.get(self.code).price, cur_price)

            # 손절 체크
            if earnings_rate < -5:
                # 손절라인
                sell_amount = 1
            # 익절 체크
            elif earnings_rate > 7:
                sell_amount = 1
            else:
                sell_amount = 0

            if sell_amount:
                self._sell(
                    dt=datetime.combine(candle.date, candle.time),
                    price=cur_price,
                    count=int(sell_amount * self.wallet.get(self.code).count)
                )

                self.wallet.sell(datetime.combine(candle.date, candle.time),
                                 self.code,
                                 sell_price=cur_price,
                                 sell_amount=sell_amount)
        else:  # 미보유 종목에 대한 매수 판단
            # 120MA < 60MA < 5MA < 20MA and 5MA 상향돌파
            if ma_120_yst < ma_60_yst < ma_5_yst < ma_20_yst and daily_candle.open < ma_5_yst <= cur_price < ma_5_yst * 1.025:
                count = int(BUY_LIMIT / cur_price)
                self.wallet.buy(datetime.combine(candle.date, candle.time), code=self.code, price=cur_price,
                                count=count)
                self._buy(datetime.combine(candle.date, candle.time), cur_price, count)


class GoldenDeadCrossSimulator(Simulator):

    def on_finished(self):
        if self.last_candle and self.wallet.has(self.code):
            self.wallet.sell(dt=datetime.combine(self.last_candle.date, self.last_candle.time),
                             code=self.last_candle.code,
                             sell_price=self.last_candle.close,
                             sell_amount=1)

        detail = details.get(self.code)

        if self.wallet.earnings:
            final_msg_items = [
                '###',
                self.code,
                detail.name,
                detail.capitalization(),
                self.wallet.earnings
            ]

            logger.critical(', '.join([str(item) for item in final_msg_items]))

    def on_candle(self, candle: Candle):
        self.last_candle = candle
        cur_price = candle.close
        ma_5_cur = self.ma(dt=candle.date, cur_price=cur_price, length=5)
        ma_5_yst = self.ma(dt=candle.date, pos=-1, length=5)
        ma_10_cur = self.ma(dt=candle.date, cur_price=cur_price, length=10)
        ma_10_yst = self.ma(dt=candle.date, pos=-1, length=10)
        ma_20_yst = self.ma(dt=candle.date, pos=-1, length=20)
        ma_60_yst = self.ma(dt=candle.date, pos=-1, length=60)
        ma_120_yst = self.ma(dt=candle.date, pos=-1, length=120)

        if self.wallet.has(code=self.code):  # 보유 종목에 대한 매도 판단
            holding = self.wallet.get(self.code)

            # max 갱신
            holding.max_price = max(holding.max_price, cur_price)

            # 수익율 계산
            earnings_rate = calc.earnings_ratio(self.wallet.get(self.code).price, cur_price)

            # 손절 체크
            if earnings_rate < -10:
                # 손절라인
                sell_amount = 1
            # 익절 체크
            elif earnings_rate > 16:
                sell_amount = 1
            else:
                sell_amount = 0

            if ma_5_yst > ma_10_yst > ma_5_cur:
                sell_amount = 1

            if sell_amount:
                self.wallet.sell(datetime.combine(candle.date, candle.time),
                                 self.code,
                                 sell_price=cur_price,
                                 sell_amount=sell_amount)

            # TODO: 넣을지 말지 확인
            # candle_time = candle.datetime.time()
            # elif 1515 < candle_time.hour * 100 + candle_time.minute < 1520 and earnings_rate > 3.5:
            #     # 장종료전에 마감해보자
            #     self.wallet.sell(candle.datetime, self.code, cur_price)
        else:  # 미보유 종목에 대한 매수 판단
            if ma_120_yst < ma_60_yst < ma_20_yst and ma_5_yst < ma_10_yst < ma_5_cur < ma_10_cur * 1.03:
                self.wallet.buy(datetime.combine(candle.date, candle.time), code=self.code, price=cur_price,
                                count=int(BUY_LIMIT / cur_price))


@dataclass
class Term:
    begin: date
    end: date


def main(codes: List[str]):
    start_time = time.time()

    # 1.9 ~ 2.1 // 3.12 ~ 6.14
    terms = [
        Term(date(2018, 1, 9), date(2018, 1, 18)),
        Term(date(2018, 3, 12), date(2018, 6, 14)),
    ]

    count = 0
    for code in codes:
        count += 1

        # if code in executed or stocks.get_name(code) in executed:
        #     continue

        logger.info(
            f'[{count}/{len(codes)}] {stocks.get_name(code)} - 시총: {details.get(code).capitalization()}')

        for term in terms:
            begin = term.begin
            end = term.end
            ep = None
            try:
                logger.info(f'{begin} ~ {end}')
                ep = BreakAbove5MaEventSimulator(code,
                                                 begin=begin,
                                                 end=end)
                ep.start()
            except NotEnoughChartException as e:
                logger.warning(str(e))
            finally:
                if ep:
                    ep.candle_provider.stop()

    logger.critical(time.time() - start_time)


if __name__ == '__main__':
    available_codes.sort(key=lambda code: details.get(code).capitalization())
    main([code for code in available_codes if '스팩' not in stocks.get_name(code)])
