# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from typing import *

from common.model import Candle


def avg(values: List[int]) -> float:
    return sum(values) / len(values)


class MaCalculator:
    """
    이동 평균 관리자
    주의: 일봉
    """

    def __init__(self, day_candles: List[Candle]):
        self.candles = day_candles

    def get(self, length: int, cur_price: int = None, pos: int = 0):
        """
        Ex) 오늘 ma 조회 get(ma, cur_price)
        Ex) 어제 ma 조회 get(ma, pos=-1)
        """

        closes = [cd.close for cd in self.candles] + [cur_price]
        assert len(closes) >= length, 'Not enough chart'
        if pos:
            return avg(closes[-length + pos: pos])
        else:
            return avg(closes[-length:])
