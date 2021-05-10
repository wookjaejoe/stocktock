# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

# 시작일부터 종료일까지 해석한다.
# 일별 총평가금액/수익율
# 보유종목 평가금 + 예수금:
# 보유종목 평가금 = 당일 시장 종료 시점에 보유 종목 종가 * 보유 개수
# 예수금 = 예수금?

import json
from datetime import date, timedelta
from typing import *

import jsons

from database.backtest2 import Backtest, BacktestEvent, BacktestEventType
from database.candles.day import DayCandleTable
from database.stocks import StockTable
from indexes import InterestIndexes
from utils import log

import logging

log.init()


def save(x: any):
    with open('.cache.json', 'w') as f:
        json.dump(jsons.dump(x), f)


def load():
    with open('.cache.json', 'r') as f:
        return jsons.loads(f.read(), Backtest)


def backtest(begin: date, end: date):
    with StockTable() as stock_table:
        all_stocks = stock_table.all()

    bt = Backtest(
        codes=[stock.code for stock in all_stocks],
        begin=begin,
        end=end,
        limit_holding_count=100,
        limit_buy_amount=100_0000,
        earn_line=1.07,
        stop_line=0.95
    )
    bt.start()
    save(bt.__dict__)


def analyze(begin: date, end: date):
    result = load()
    indexes = InterestIndexes.load(begin, end)
    result.events = jsons.load(result.events, List[BacktestEvent])
    for event in result.events:
        logging.info(', '.join([str(v) for v in event.__dict__.values()]))

    holdings = {}
    initial_deposite = 5_0000_0000
    deposite = initial_deposite
    for day in [result.begin + timedelta(days=days) for days in range((result.end - result.begin).days)]:
        events: List[BacktestEvent] = [event for event in result.events if event.when.date() == day]
        for event in events:
            if event.type == BacktestEventType.BUY:
                deposite -= event.price * event.count
                holdings.update({event.code: event})
            elif event.type == BacktestEventType.SELL:
                deposite += event.price * event.count
                del holdings[event.code]

        holding_evaluation = 0
        skip = False
        for code in holdings.keys():
            try:
                with DayCandleTable(code) as day_candles_table:
                    day_candle = day_candles_table.find_by_date(day)
                    holding_evaluation += day_candle.close * holdings.get(code).count
            except:
                skip = True
                break

        if not skip:
            try:
                appendix = [
                    indexes.kospi.values.get(day).close,  # 코스피
                    indexes.kospi_50.values.get(day).close,  # 코스피 50
                    indexes.kospi_100.values.get(day).close,  # 코스피 100
                    indexes.kospi_200.values.get(day).close,  # 코스피 200
                    indexes.kosdaq.values.get(day).close,  # 코스닥
                    indexes.kosdaq_150.values.get(day).close,  # 코스닥 150
                    indexes.krx_100.values.get(day).close,  # 한국거래소 100
                    indexes.krx_300.values.get(day).close,  # 한국거래소 300
                ]
            except:
                appendix = []

            values = [
                day,  # 날짜
                deposite,  # 예수금
                holding_evaluation,  # 보유 종목 현재가 총액
                deposite + holding_evaluation,  # 평가 금액
                len(holdings.keys()),  # 보유 종목 개수
                (deposite + holding_evaluation) / initial_deposite,  # 수익율
                *appendix
            ]

            print(', '.join([str(v) for v in values]))


def main():
    begin = date.today() - timedelta(days=100)
    end = date.today()
    # print(begin, end)
    # backtest(begin, end)
    analyze(begin, end)


if __name__ == '__main__':
    main()
