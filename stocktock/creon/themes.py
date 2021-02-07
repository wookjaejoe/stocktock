from dataclasses import dataclass
from enum import Enum

import win32com.client

from creon.com import limit_safe, ReqType


@limit_safe(req_type=ReqType.NON_TRADE)
def get_themes():
    cpsvr_8561 = win32com.client.Dispatch('Dscbo1.CpSvr8561')
    cpsvr_8561.BlockRequest()
    count = cpsvr_8561.GetHeaderValue(0)
    result = {}
    for i in range(count):
        theme_code = cpsvr_8561.GetDataValue(0, i)
        # theme_seq = cpsvr_8561.GetDataValue(1, i)
        theme_name = cpsvr_8561.GetDataValue(2, i)
        result.update({theme_code: theme_name})

    return result


def get_theme(code: str):
    cpsvr_8562 = win32com.client.Dispatch('Dscbo1.CpSvr8562')
    cpsvr_8562.SetInputValue(0, code)
    cpsvr_8562.BlockRequest()
    count = cpsvr_8562.GetHeaderValue(0)
    theme_codes = []
    for i in range(count):
        theme_code = cpsvr_8562.GetDataValue(0, i)
        theme_codes.append(theme_code)
    return theme_codes


ALL_THEMES = get_themes()


@dataclass
class StockByTheme:
    theme_code: int
    theme_name: str
    code: str
    name: str
    price: int
    margin: int
    margin_percentage: float
    vol: int
    arg_6: float  # (float) 전일동시간대비


@limit_safe(req_type=ReqType.NON_TRADE)
def get_stocks(theme_code):
    cpsvr_8561t = win32com.client.Dispatch('Dscbo1.CpSvr8561T')
    cpsvr_8561t.SetInputValue(0, theme_code)
    cpsvr_8561t.BlockRequest()
    count = cpsvr_8561t.GetHeaderValue(1)
    comment = cpsvr_8561t.GetHeaderValue(2)

    result = []
    for i in range(count):
        stock_by_theme = StockByTheme(
            theme_code=theme_code,
            theme_name=ALL_THEMES.get(theme_code),
            code=cpsvr_8561t.GetDataValue(0, i),
            name=cpsvr_8561t.GetDataValue(1, i),
            price=cpsvr_8561t.GetDataValue(2, i),
            margin=cpsvr_8561t.GetDataValue(3, i),
            margin_percentage=cpsvr_8561t.GetDataValue(4, i),
            vol=cpsvr_8561t.GetDataValue(5, i),
            arg_6=cpsvr_8561t.GetDataValue(6, i)
        )
        result.append(stock_by_theme)

    return result


class RankingType(Enum):
    HIGHEST_MARGIN_1 = '1'
    LOWEST_MARGIN_1 = '2'
    HIGHEST_MARGIN_5 = '3'
    LOWEST_MARGIN_5 = '4'
    UPPER_RATE_OF_RISING_STOCKS = '5'
    LOWER_RATE_OF_RISING_STOCKS = '6'


@dataclass
class RankingItem:
    theme_code: str
    theme_name: str
    stock_count: int
    margin_1: int
    margin_5: int
    increased_count: int
    decreased_count: int
    increased_rate: float


@limit_safe(req_type=ReqType.NON_TRADE)
def get_ranking(ranking_type: RankingType):
    cpsvr_8563 = win32com.client.Dispatch('Dscbo1.CpSvr8563')
    cpsvr_8563.SetInputValue(0, ranking_type.value)
    cpsvr_8563.BlockRequest()
    count = cpsvr_8563.GetHeaderValue(0)
    result = []
    for i in range(count):
        ranking_item = RankingItem(
            theme_code=cpsvr_8563.GetDataValue(0, i),
            theme_name=cpsvr_8563.GetDataValue(1, i),
            stock_count=cpsvr_8563.GetDataValue(2, i),
            margin_1=cpsvr_8563.GetDataValue(3, i),
            margin_5=cpsvr_8563.GetDataValue(4, i),
            increased_count=cpsvr_8563.GetDataValue(5, i),
            decreased_count=cpsvr_8563.GetDataValue(6, i),
            increased_rate=cpsvr_8563.GetDataValue(7, i)
        )
        result.append(ranking_item)
        
    return result


def example():
    get_ranking(ranking_type=RankingType.HIGHEST_MARGIN_1)


if __name__ == '__main__':
    example()
