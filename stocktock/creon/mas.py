import logging
from enum import Enum
from typing import *

from creon import charts
from database import dailycharts


class MA(Enum):
    MA_5 = 5
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

    def __init__(self, code: str, chart: List[charts.ChartData] = None):
        self.code = code

        if chart is not None:
            self.chart = chart
        else:
            self.chart = charts.request(
                code=code,
                chart_type=charts.ChartType.DAY,
                count=120
            )

    def get(self, ma_type: MA, cur_price=0, pos=0):
        """
        Ex) 오늘 ma 조회 get(ma, cur_price)
        Ex) 어제 ma 조회 get(ma, pos=-1)

        """
        if pos:
            return avg([cd.close for cd in self.chart[-ma_type.value + pos: pos]])
        else:
            assert cur_price, 'Incorrect code: cur_price is not presented.'
            # 최근 n-1개 데이터 및 현재가의 평균
            return avg([cd.close for cd in self.chart[-ma_type.value:]] + [cur_price])

    def is_straight(self, cur_price):
        ma_20 = self.get(ma_type=MA.MA_20, cur_price=cur_price)
        ma_60 = self.get(ma_type=MA.MA_60, cur_price=cur_price)
        ma_120 = self.get(ma_type=MA.MA_120, cur_price=cur_price)
        return ma_20 > ma_60 > ma_120


_calc_pool: Dict[str, MaCalculator] = {}


def init_pool():
    logging.debug('Loading chart data from dataabase...')

    for chart_data in dailycharts.find():
        if chart_data.code not in _calc_pool:
            _calc_pool.update({chart_data.code: MaCalculator(chart_data.code, [])})

        _calc_pool.get(chart_data.code).chart.append(chart_data)

    logging.debug('FINISHED - The initialzation for MA calculator pool')


init_pool()


def get_calculator(code: str):
    if code not in _calc_pool:
        _calc_pool.update({code: MaCalculator(code)})

    return _calc_pool.get(code)
