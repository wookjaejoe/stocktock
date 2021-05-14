# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from typing import *

from common.metric import MaCalculator
from common.model import Candle
from .common import Strategy


class Over5MaStrategy(Strategy):

    def __init__(
            self,
            earn_percent: float,
            stop_percent: float
    ):
        self.earn_percent = earn_percent
        self.stop_percent = stop_percent

    def check_and_buy(
            self,
            day_candles: List[Candle],
            cur_price: int,
            buy: Callable
    ):
        try:
            ma_calc = MaCalculator(day_candles)
            ma_5_yst = ma_calc.get(5, pos=-1)
            if day_candles[-1].open < ma_5_yst < cur_price < ma_5_yst * 1.025:
                buy()
        except:
            return

    def check_and_sell(self):
        pass
