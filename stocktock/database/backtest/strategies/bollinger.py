import logging
import statistics
from dataclasses import dataclass
from datetime import date
from datetime import timedelta, datetime
from typing import *

from common.model import CandlesGroupByCode
from database.charts import DayCandlesTable, MinuteCandlesTable
from ..backtest import AbcBacktest


@dataclass
class BollingerBand:
    mid: float
    upper: float
    lower: float

    class NotEnoughArgs(Exception): ...

    @classmethod
    def of(cls, prices: List[float], size: int):
        if not len(prices) > size:
            raise cls.NotEnoughArgs(f'{len(prices)} input, but {size} needed.')

        prices = prices[-size:]
        ma = sum(prices) / size

        return BollingerBand(
            upper=ma + (2 * statistics.pstdev(prices)),
            lower=ma - (2 * statistics.pstdev(prices)),
            mid=ma
        )


def is_overlap(bound_1: Tuple[float, float], bound_2: Tuple[float, float]):
    return bound_2[0] <= bound_1[0] <= bound_2[1] \
           or bound_2[0] <= bound_1[1] <= bound_2[1] \
           or bound_1[0] <= bound_2[0] <= bound_1[1] \
           or bound_1[0] <= bound_2[1] <= bound_1[1]


class BackTest(AbcBacktest):
    """
    볼린저 밴드 기반 매매 전략:
    - 코스피 200 종목에 대해
    - 볼린저 밴드:
        - MID: 20MA
        - UPPER/LOWER: 20MA +- 표준편차 * 2
    - 매수: 현재가 < LOWER
    - 매도: 공통 매도 조건, 손절 -10%
        - 트레일링 스탑: 스탑 기준을 고점 대비 -3%
        - 최소 익절 조건: 5%
        - 분할: 10%, 15%
    - 종목 당 전체 시드의 5%씩 투자
    """

    BOLLINGER_SIZE = 20

    def __init__(
            self, available_codes: List[str], begin: date, end: date, initial_deposit: int, once_buy_amount: int,
            earning_line_min: float, earning_line: float, earning_line_max: float, stop_line: float,
            trailing_stop_rate: float
    ):
        super().__init__(available_codes, begin, end, initial_deposit)
        self.once_buy_amount = once_buy_amount
        self.earning_line_min = earning_line_min
        self.earning_line = earning_line
        self.earning_line_max = earning_line_max
        self.stop_line = stop_line
        self.trailing_stop_rate = trailing_stop_rate

    def run(self, today: date):
        with DayCandlesTable() as day_candles_table:
            day_candles = day_candles_table.find_all_in(
                codes=self.available_codes,
                begin=today - timedelta(days=self.BOLLINGER_SIZE * 2),
                end=today
            )

            if not day_candles:
                return

        day_candles_by_code = CandlesGroupByCode(day_candles)

        whitelist = []
        for code in day_candles_by_code.codes():
            day_candles = day_candles_by_code.get(code)

            try:
                blg_with_high = BollingerBand.of(
                    [candle.close for candle in day_candles[:-1]] + [day_candles[-1].high],
                    self.BOLLINGER_SIZE
                )
            except BollingerBand.NotEnoughArgs:
                continue

            today_candle = day_candles_by_code.get(code)[-1]
            if blg_with_high.lower > today_candle.low:
                whitelist.append(code)

        logging.info(f'{len(whitelist)} codes in whitelist.')
        with MinuteCandlesTable(d=today) as minute_candles_table:
            minute_candles = minute_candles_table.find_all(codes=whitelist + [code for code in self.account.holdings])

        logging.info(f'{len(self.account.holdings)} codes in holding.')

        blacklist = []
        minute_candles.sort(key=lambda mc: datetime.combine(mc.date, mc.time))
        for minute_candle in minute_candles:
            now = minute_candle.datetime()
            code = minute_candle.code
            price = minute_candle.close

            if self.account.has(code):
                # 보유중 - 매도 시그널 확인
                holding = self.account.holdings.get(code)

                # 최고가 업데이트
                if price > holding.max:
                    holding.max = price

                revenue = price - holding.avg_price
                revenue_rate = revenue / holding.avg_price * 100

                if revenue_rate <= self.stop_line:
                    self._try_sell(when=now, code=code, price=price, amount_rate=1,
                                   comment=f'손절 {self.stop_line}')
                    blacklist.append(code)
                    continue

                if revenue_rate >= self.earning_line_min:
                    if revenue_rate >= self.earning_line_max:
                        self._try_sell(when=now, code=code, price=price, amount_rate=1,
                                       comment=f'전량 익절 {self.earning_line_max}%+')
                        continue
                    if (price - holding.max) / holding.max * 100 < -abs(self.trailing_stop_rate):  # 트레일링 스탑
                        self._try_sell(when=now, code=code, price=price, amount_rate=1,
                                       comment=f'트레일링 스탑: 고점({holding.max}) 대비 {(price - holding.max) / holding.max * 100}%')
                        continue
                    if revenue_rate >= self.earning_line and not hasattr(holding, 'mark'):
                        holding.mark = True
                        self._try_sell(when=now, code=code, price=price, amount_rate=1 / 2,
                                       comment=f'절반 익절 {self.earning_line}%+')
                        continue

            else:
                if code in blacklist:
                    continue

                bollinger = BollingerBand.of(
                    prices=[dc.close for dc in day_candles_by_code.get(code)[:-1]] + [price],
                    size=self.BOLLINGER_SIZE
                )

                # 미보유 - 매수 시그널 확인
                if minute_candle.close < bollinger.lower:
                    self._try_buy(
                        when=now, code=code,
                        price=minute_candle.close,
                        amount=self.once_buy_amount,
                        comment='현재가 밴드 하단'
                    )
