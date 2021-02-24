import logging
from enum import Enum
from typing import *

from creon import charts
from database import dailycharts
from datetime import date, timedelta


class MA(Enum):
    MA_5 = 5
    MA_10 = 10
    MA_20 = 20
    MA_60 = 60
    MA_120 = 120


def avg(values: List[int]) -> float:
    if values:
        return sum(values) / len(values)
    else:
        return 0


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
                count=150
            )

    def get(self, ma_type: MA, cur_price=0, pos=0):
        """
        Ex) 오늘 ma 조회 get(ma, cur_price)
        Ex) 어제 ma 조회 get(ma, pos=-1)
        """
        closes = [cd.close for cd in self.chart] + [cur_price]
        return avg(closes[-ma_type.value + pos: pos])

    def is_straight(self):
        ma_20 = self.get(ma_type=MA.MA_20, pos=-1)
        ma_60 = self.get(ma_type=MA.MA_60, pos=-1)
        ma_120 = self.get(ma_type=MA.MA_120, pos=-1)
        return ma_20 > ma_60 > ma_120


_calc_pool: Dict[str, MaCalculator] = {}


def init_pool():
    logging.info('Loading chart data from...')
    for chart_data in dailycharts.load_cache():
        if chart_data.code not in _calc_pool:
            _calc_pool.update({chart_data.code: MaCalculator(chart_data.code, [])})

        _calc_pool.get(chart_data.code).chart.append(chart_data)

    yesterday = date.today() - timedelta(days=1)
    if max([cd.datetime for cd in list(_calc_pool.values())[0].chart]).date() != yesterday:
        logging.warning('!!! CHART MAY BE NOT UPDATED !!!')

    logging.info('FINISHED - The initialzation for MA calculator pool')


init_pool()


def get_calculator(code: str):
    if code not in _calc_pool:
        _calc_pool.update({code: MaCalculator(code)})

    return _calc_pool.get(code)
