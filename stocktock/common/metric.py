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

    def __init__(self, values: List[int]):
        self.values = values

    def get(self, length: int, pos: int = 0):
        assert len(self.values) >= length, 'Not enough chart'
        return avg(self.values[-length + pos: pos])
