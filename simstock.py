import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import *

from utils import calc, log

log.init(logging.DEBUG)
import simulation.events

from creon import charts, stocks

logger = logging.getLogger()


@dataclass
class Holding:
    code: str
    count: int
    price: int


BUY_LIMIT = 200_0000


class Wallet:

    def __init__(self):
        self.holdings: List[Holding] = []

    def has(self, code):
        return code in [holding.code for holding in self.holdings]

    def get(self, code):
        for holding in self.holdings:
            if code == holding.code:
                return holding

    # 로그: 시각, 주문타입, 종목코드, 종목명, 주문가, 주문수량, 주문총액, 수익율, 수익금
    def buy(self, dt: datetime, code, count, price):
        tokens = [
            dt,
            'BUY',
            code,
            stocks.get_name(code),
            price,
            count,
            price * count, 0, 0
        ]

        logger.critical(', '.join([str(token) for token in tokens]))
        self.holdings.append(Holding(code, count, price))

    def sell(self, dt: datetime, code, sell_price):
        holding = self.get(code)
        earning_rate = calc.earnings_ratio(holding.price, sell_price)

        tokens = [
            dt,
            'SELL',
            code,
            stocks.get_name(code),
            sell_price,
            holding.count,
            sell_price * holding.count,
            earning_rate,
            sell_price * holding.count - holding.price * holding.count,
            len(self.holdings)
        ]

        logger.critical(', '.join([str(token) for token in tokens]))
        self.holdings.remove(self.get(code))


class NotEnoughChartException(BaseException):
    def __init__(self, code, name):
        self.code = code
        self.name = name

    def __str__(self):
        return f'Not enough chart for {self.name}({self.code})'


class BreakAbove5MaEventPublisher:

    def __init__(self, code: str, begin: date, end: date):
        self.wallet = Wallet()
        self.code = code
        self.candle_provider = simulation.events.PastMinuteCandleProvdider(code, begin, end)
        self.candle_provider.subscribers.append(self.check_break_above_5ma)
        self.daily_candles: List[charts.ChartData] = charts.request_by_term(
            code=code,
            chart_type=charts.ChartType.DAY,
            begin=begin - timedelta(days=250),
            end=end
        )

        self.daily_candles.sort(key=lambda candle: candle.datetime)

        if not self.daily_candles[0].datetime.date() < begin < self.daily_candles[-1].datetime.date():
            raise NotEnoughChartException(code=code, name=stocks.get_name(code))

        self.daily_candles: Dict[date, charts.ChartData] = {candle.datetime.date(): candle
                                                            for candle in self.daily_candles}

    def ma(self, dt: date, length: int):
        closes = [candle.close for candle in self.daily_candles.values()
                  if candle.datetime.date() <= dt][-length:]

        if length > len(closes):
            raise NotEnoughChartException(self.code, stocks.get_name(self.code))

        return sum(closes) / length

    def ma_5(self, dt: date):
        return self.ma(dt, 5)

    def ma_20(self, dt: date):
        return self.ma(dt, 20)

    def ma_60(self, dt: date):
        return self.ma(dt, 60)

    def ma_120(self, dt: date):
        return self.ma(dt, 120)

    def start(self):
        self.candle_provider.start()

    def check_break_above_5ma(self, candle: charts.ChartData):
        ma_5 = self.ma_5(candle.datetime.date() - timedelta(days=1))
        ma_20 = self.ma_20(candle.datetime.date() - timedelta(days=1))
        ma_60 = self.ma_60(candle.datetime.date() - timedelta(days=1))
        ma_120 = self.ma_120(candle.datetime.date() - timedelta(days=1))

        cur_price = candle.close
        daily_candle = self.daily_candles.get(candle.datetime.date())

        if self.wallet.has(code=self.code):
            earnings_rate = calc.earnings_ratio(self.wallet.get(self.code).price, cur_price)
            candle_time = candle.datetime.time()
            if earnings_rate > 7:
                self.wallet.sell(candle.datetime, self.code, sell_price=cur_price)
            elif earnings_rate < -5:
                self.wallet.sell(candle.datetime, self.code, sell_price=cur_price)

            elif 1515 < candle_time.hour * 100 + candle_time.minute < 1520 and earnings_rate > 3.5:
                # 장종료전에 마감해보자
                self.wallet.sell(candle.datetime, self.code, cur_price)
        else:
            # 정배열 판단 & daily_candle.open < ma_5 <= cur_price < ma_5 * 1.02
            if ma_120 < ma_60 < ma_20 < daily_candle.open < ma_5 <= cur_price < ma_5 * 1.02:
                self.wallet.buy(candle.datetime, code=self.code, price=cur_price, count=int(BUY_LIMIT / cur_price))


def main():
    start_time = time.time()
    available_codes = stocks.get_availables()

    count = 0
    for code in available_codes:
        count += 1
        logger.info(f'[{count}/{len(available_codes)}] {stocks.get_name(code)}')

        ep = None
        try:
            ep = BreakAbove5MaEventPublisher(code,
                                             begin=date(year=2020, month=8, day=1),
                                             end=date.today())
            ep.start()
        except NotEnoughChartException as e:
            logger.warning(str(e))
        finally:
            if ep:
                ep.candle_provider.stop()

    logger.critical(time.time() - start_time)


if __name__ == '__main__':
    main()
