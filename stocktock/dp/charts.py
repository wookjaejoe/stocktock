from datetime import date
from typing import *

import database as db
from creon import charts as creon_charts
from creon import stocks as creon_stocks
from model import Candle


# 일 차트 기간 조회
def get_day_candles(code: str, begin: date, end: date) -> List[Candle]:
    assert len(code) == 6, 'Malformed stock code'

    candles = creon_charts.request_by_term(
        code=creon_stocks.find(code).code,
        chart_type=creon_charts.ChartType.DAY,
        begin=begin,
        end=end
    )

    stock_id = db.Stock.find_by_code(code).id

    for candle in candles:
        if not db.DayCandle.exists(stock_id=stock_id, date=candle.date):
            db.DayCandle(
                stock_id=stock_id,
                date=candle.date,
                time=candle.time,
                open=candle.open,
                close=candle.close,
                low=candle.low,
                high=candle.high
            ).insert(do_commit=True)

    return candles


# 분 차트 기간 조회
def get_minute_candles(code: str, begin: date, end: date) -> List[Candle]:
    dates = [candle.date for candle in get_day_candles(code, begin, end)]

    # db 조회
    candles = db.MinuteCandle.query().filter(begin < db.MinuteCandle.date < end)
    stock_id = db.Stock.find_by_code(code).id

    for d in dates:
        if not db.MinuteCandle.exists(stock_id=stock_id, date=d):
            pass

    return candles
