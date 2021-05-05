from typing import *

from database.candles.day import DayCandle


def avg(values: List[int]) -> float:
    return sum(values) / len(values)


class MaCalculator:
    """
    이동 평균 관리자
    주의: 일봉
    """

    def __init__(self, candles: List[DayCandle] = None):
        self.candles = candles

    def get(self, length: int, cur_price: int = None, pos: int = 0):
        """
        Ex) 오늘 ma 조회 get(ma, cur_price)
        Ex) 어제 ma 조회 get(ma, pos=-1)
        """

        closes = [cd.close for cd in self.candles] + [cur_price]
        if pos:
            assert len(closes) >= -length + pos, 'Not enough chart'
            return avg(closes[-length + pos: pos])
        else:
            assert len(closes) >= -length, 'Not enough chart'
            return avg(closes[-length:])
