import logging
import math
import time
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import *

from utils import calc, log

log.init(logging.DEBUG)
import simulation.events

from creon import charts, stocks

logger = logging.getLogger()

available_codes = stocks.get_availables()
available_codes = [code for code in available_codes if stocks.get_capital_type(code) == 3]

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
SEED = 1_0000_0000


class Wallet:

    def __init__(self):
        self.holdings: List[Holding] = []

    def has(self, code):
        return code in [holding.code for holding in self.holdings]

    def get(self, code):
        for holding in self.holdings:
            if code == holding.code:
                return holding

    def buy(self, dt: datetime, code, count, price):
        global SEED
        total = count * price

        if total > SEED:
            logger.critical(f'시드부족. 남은현찰: {SEED}')
            return

        self.holdings.append(Holding(code, count, price))
        SEED -= total
        tokens = [
            dt,  # 주문시각
            'BUY',  # 구분
            code,  # 종목코드
            details.get(code).capitalization(),
            stocks.get_name(code),  # 종목명
            price,  # 주문가
            count,  # 주문수량
            total,  # 주문총액
            'N/A',  # 수익율
            'N/A',  # 수익금
            count,  # 잔여수량
            SEED  # 남은 시드
        ]

        logger.critical(', '.join([str(token) for token in tokens]))

    def sell(self, dt: datetime, code, sell_price, sell_amount: float):
        global SEED
        holding = self.get(code)

        # 매도 수량 계산
        sell_count = math.ceil(holding.count * sell_amount)

        # 보유 수량에서 매도 수량 만큼 차감
        holding.count = holding.count - sell_count
        if holding.count == 0:
            # 전량 매도
            self.holdings.remove(holding)

        SEED += sell_price * sell_count
        tokens = [
            dt,  # 시각
            'SELL',  # 구분
            code,  # 종목코드
            stocks.get_name(code),  # 종목명
            details.get(code).capitalization(),  #
            sell_price,  # 주문가
            sell_count,  # 주문수량
            sell_price * sell_count,  # 주문총액
            calc.earnings_ratio(holding.price, sell_price),  # 수익율
            sell_price * sell_count - holding.price * sell_count,  # 수익금
            holding.count,  # 잔여수량
            SEED  # 남은 시드
        ]

        logger.critical(', '.join([str(token) for token in tokens]))


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
            begin=begin - timedelta(days=200),
            end=end
        )

        self.daily_candles.sort(key=lambda candle: candle.datetime)

        if not self.daily_candles[0].datetime.date() < begin < self.daily_candles[-1].datetime.date():
            raise NotEnoughChartException(code=code, name=stocks.get_name(code))

        self.daily_candles: Dict[date, charts.ChartData] = {candle.datetime.date(): candle
                                                            for candle in self.daily_candles}
        self.last_candle: charts.ChartData = None

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
        self.on_finished()

    def on_finished(self):
        if self.last_candle and self.wallet.has(self.code):
            self.wallet.sell(dt=self.last_candle.datetime,
                             code=self.last_candle.code,
                             sell_price=self.last_candle.close,
                             sell_amount=1)

    def check_break_above_5ma(self, candle: charts.ChartData):
        self.last_candle = candle
        ma_5 = self.ma_5(candle.datetime.date() - timedelta(days=1))
        ma_20 = self.ma_20(candle.datetime.date() - timedelta(days=1))
        ma_60 = self.ma_60(candle.datetime.date() - timedelta(days=1))
        ma_120 = self.ma_120(candle.datetime.date() - timedelta(days=1))

        cur_price = candle.close
        daily_candle = self.daily_candles.get(candle.datetime.date())

        if self.wallet.has(code=self.code):  # 보유 종목에 대한 매도 판단
            holding = self.wallet.get(self.code)

            # max 갱신
            holding.max_price = max(holding.max_price, cur_price)

            # 수익율 계산
            earnings_rate = calc.earnings_ratio(self.wallet.get(self.code).price, cur_price)

            # 손절 체크
            if earnings_rate < -4:
                # 손절라인
                self.wallet.sell(candle.datetime, self.code, sell_price=cur_price, sell_amount=1)
            # 익절 체크
            elif earnings_rate > 5:
                if holding.max_price * 0.97 > cur_price:
                    # max * 0.97 > 현재가: 모두 매도
                    sell_amount = 1
                elif earnings_rate > 15:
                    # 익절라인
                    sell_amount = 1
                elif not holding.is_10_beneath and earnings_rate > 10:
                    # 익절라인 12%: 2/3 매도
                    sell_amount = 1 / 2
                    holding.is_10_beneath = True
                elif not holding.is_5_beneath:
                    # 익절라인 5%: 1/3 매도
                    sell_amount = 1 / 3
                    holding.is_5_beneath = True
                else:
                    sell_amount = 0
            elif holding.is_5_beneath:
                # 5% 작은데, 5% 찍은적이 있다? 그럼 다 팔아
                sell_amount = 1
            else:
                sell_amount = 0

            if sell_amount:
                self.wallet.sell(candle.datetime,
                                 self.code,
                                 sell_price=cur_price,
                                 sell_amount=sell_amount)

            # TODO: 넣을지 말지 확인
            # candle_time = candle.datetime.time()
            # elif 1515 < candle_time.hour * 100 + candle_time.minute < 1520 and earnings_rate > 3.5:
            #     # 장종료전에 마감해보자
            #     self.wallet.sell(candle.datetime, self.code, cur_price)
        else:  # 미보유 종목에 대한 매수 판단
            # 정배열 판단 & daily_candle.open < ma_5 <= cur_price < ma_5 * 1.02
            if ma_120 < ma_60 < ma_20 < daily_candle.open < ma_5 <= cur_price < ma_5 * 1.02:
                self.wallet.buy(candle.datetime, code=self.code, price=cur_price, count=int(BUY_LIMIT / cur_price))


def main():
    start_time = time.time()

    count = 0
    for code in available_codes:
        count += 1
        logger.info(
            f'[{count}/{len(available_codes)}] {stocks.get_name(code)} - 시총: {details.get(code).capitalization()}')

        ep = None
        try:
            ep = BreakAbove5MaEventPublisher(code,
                                             begin=date(year=2020, month=8, day=1),
                                             end=date(year=2021, month=2, day=14))
            ep.start()
        except NotEnoughChartException as e:
            logger.warning(str(e))
        finally:
            if ep:
                ep.candle_provider.stop()

    logger.critical(time.time() - start_time)


if __name__ == '__main__':
    main()
