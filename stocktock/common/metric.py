# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from typing import *


class NotEnoughChartException(BaseException):
    def __str__(self):
        return f'Not enough chart'


def avg(values: List[int]) -> float:
    return sum(values) / len(values)


class MaCalculator:
    def __init__(self, values: List[int]):
        self.values = values

    def get(self, length: int, pos: int = 0):
        if len(self.values) < length:
            raise NotEnoughChartException()

        if pos:
            return avg(self.values[-length + pos: pos])
        else:
            return avg(self.values[-length:])
