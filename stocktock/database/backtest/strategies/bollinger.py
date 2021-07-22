import logging
import statistics
from dataclasses import dataclass
from datetime import date
from datetime import timedelta, datetime
from typing import *

from common.model import CandlesGroupByCode
from database.charts import DayCandlesTable, MinuteCandlesTable
from krx import kospi_n_codes
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

    BOLLINGER_SIZE = 20

    def __init__(
            self, begin: date, end: date, initial_deposit: int, once_buy_amount: int,
            earning_line_min: float, earning_line: float, earning_line_max: float, stop_line: float,
            trailing_stop_rate: float
    ):
        super().__init__(begin, end, initial_deposit)
        self.once_buy_amount = once_buy_amount
        self.earning_line_min = earning_line_min
        self.earning_line = earning_line
        self.earning_line_max = earning_line_max
        self.stop_line = stop_line
        self.trailing_stop_rate = trailing_stop_rate

    def run(self, today: date):
        with DayCandlesTable() as day_candles_table:
            day_candles = day_candles_table.find_all_in(
                codes=kospi_n_codes(today, 300) + list(self.account.holdings.keys()),
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

        minute_candles_by_minute = {}
        for minute_candle in minute_candles:
            now = minute_candle.datetime()
            if now not in minute_candles_by_minute:
                minute_candles_by_minute.update({now: []})
            minute_candles_by_minute.get(now).append(minute_candle)

        for minute in minute_candles_by_minute:
            for minute_candle in minute_candles_by_minute.get(minute):
                now = minute_candle.datetime()
                code = minute_candle.code
                price = minute_candle.close
                bollinger = BollingerBand.of(
                    prices=[dc.close for dc in day_candles_by_code.get(code)[:-1]] + [price],
                    size=self.BOLLINGER_SIZE
                )

                if self.account.has(code):
                    # 보유중 - 매도 시그널 확인
                    holding = self.account.holdings.get(code)

                    # 최고가 업데이트
                    if price > holding.max:
                        holding.max = price

                    revenue = price - holding.avg_price
                    revenue_rate = revenue / holding.avg_price * 100

                    # 밴드 중단 매도
                    # if price > bollinger.mid:
                    #     self._try_sell(when=now, code=code, price=price, amount_rate=1,
                    #                    comment=f'현재가 밴드 중단')
                    #     if revenue_rate < 0:
                    #         blacklist.append(code)
                    #     continue

                    if revenue_rate <= self.stop_line:
                        # 추가매수
                        if code not in blacklist:
                            self._try_buy(
                                when=now, code=code,
                                price=minute_candle.close,
                                amount=self.once_buy_amount,
                                comment=f'추가매수(평단: {holding.avg_price}, 현재가 평단 대비: {revenue_rate})'
                            )

                        # 손절
                        # self._try_sell(when=now, code=code, price=price, amount_rate=1,
                        #                comment=f'손절 {self.stop_line}')
                        blacklist.append(code)
                        continue

                    if revenue_rate >= self.earning_line_min:
                        # 익절
                        if revenue_rate >= self.earning_line_max:
                            self._try_sell(when=now, code=code, price=price, amount_rate=1,
                                           comment=f'전량 익절 {self.earning_line_max}%+')
                            continue
                        # if (price - holding.max) / holding.max * 100 < -abs(self.trailing_stop_rate):  # 트레일링 스탑
                        #     self._try_sell(when=now, code=code, price=price, amount_rate=1,
                        #                    comment=f'트레일링 스탑: 고점({holding.max}) 대비 {(price - holding.max) / holding.max * 100}%')
                        #     continue
                        # if revenue_rate >= self.earning_line and not hasattr(holding, 'mark'):
                        #     holding.mark = True
                        #     self._try_sell(when=now, code=code, price=price, amount_rate=1 / 2,
                        #                    comment=f'절반 익절 {self.earning_line}%+')
                        #     continue

                else:
                    # 미보유 - 매수 시그널 확인
                    if price < bollinger.lower and code not in blacklist:
                        self._try_buy(
                            when=now, code=code,
                            price=minute_candle.close,
                            amount=self.once_buy_amount,
                            comment='현재가 밴드 하단'
                        )
