import logging
from enum import Enum
from typing import *

from creon import charts
from model import Candle


class MA(Enum):
    MA_5 = 5
    MA_10 = 10
    MA_20 = 20
    MA_60 = 60
    MA_120 = 120


def avg(values: List[int]) -> float:
    return sum(values) / len(values)


class MaCalculator:
    """
    이동 평균 관리자
    주의: 일봉
    """

    def __init__(self, code: str, chart: List[Candle] = None):
        logging.debug('Creating a MA Calculator for ' + code)
        self.code = code

        if chart is not None:
            self.chart = chart
        else:
            self.chart = charts.request(
                code=code,
                chart_type=charts.ChartType.DAY,
                count=150
            )

    def get(self, length: int, cur_price=0, pos=0):
        """
        Ex) 오늘 ma 조회 get(ma, cur_price)
        Ex) 어제 ma 조회 get(ma, pos=-1)
        """

        closes = [cd.close for cd in self.chart] + [cur_price]
        if pos:
            assert len(closes) >= -length + pos, 'Not enough chart'
            return avg(closes[-length + pos: pos])
        else:
            assert len(closes) >= -length, 'Not enough chart'
            return avg(closes[-length:])

    def is_straight(self):
        try:
            ma_20 = self.get(length=20, pos=-1)
            ma_60 = self.get(length=60, pos=-1)
            ma_120 = self.get(length=120, pos=-1)
            return ma_20 > ma_60 > ma_120
        except:
            logging.warning(f'Failed to check {self.code} is straight')
            return False


_calc_pool: Dict[str, MaCalculator] = {}


def get_calculator(code: str):
    if code not in _calc_pool:
        _calc_pool.update({code: MaCalculator(code)})

    return _calc_pool.get(code)
