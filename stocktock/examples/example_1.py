"""
종목 정보 및 재무 제표 정보 획득
"""

from datetime import date
from typing import *

from database.charts import DayCandlesTable
from database.fundamental import FundamentalTable
from database.stocks import StockTable


def print_items(items: List[Any]) -> None:
    for item in items:
        print(item)


def main():
    # 모든 종목 정보 조회
    with StockTable() as stock_table:
        result = stock_table.all()
        print_items(result)

    # 종목 코드로 특정 종목 조회
    with StockTable() as stock_table:
        result = stock_table.find('005930')  # 삼성전자 주식 정보 가져오기
        print(result)

    # 특정 종목 일자별 제무재표 조회
    with FundamentalTable(code='005930') as fundamental_table:
        result = fundamental_table.all()  # 삼성전자 일자별 재무재표 조회
        print_items(result)

    # 여러 종목 일봉 차트 조회
    with DayCandlesTable() as day_candles_table:
        codes = ['005930', '000660', '035720']

        # 2020-01-01 ~
        result = day_candles_table.find_all_in(codes=codes, begin=date(2020, 1, 1))
        print_items(result)

        # ~ 2020-01-01
        result = day_candles_table.find_all_in(codes=codes, end=date(2020, 1, 1))
        print_items(result)

        # 2020-01-01 ~ 2020-12-31
        result = day_candles_table.find_all_in(codes=codes, begin=date(2020, 1, 1), end=date(2020, 12, 31))
        print_items(result)


if __name__ == '__main__':
    main()
