import abc
import logging
from datetime import date, timedelta, datetime
from multiprocessing.pool import ThreadPool
from typing import *

import pykrx.stock

import database as db
import utils.log
from creon import charts, stocks

utils.log.init()


def date_to_str(d: date) -> str:
    def two_digits(n: int):
        return str(n).rjust(2, '0')

    return f'{d.year}{two_digits(d.month)}{two_digits(d.day)}'


def _business_days(limit=10 * 365) -> List[date]:
    fromdate = date_to_str(date.today() - timedelta(days=limit))
    todate = date_to_str(date.today())

    big_stocks = [
        pykrx.stock.get_market_ohlcv_by_date(
            fromdate=fromdate,
            todate=todate,
            ticker='005930'  # 삼성전자
        ),
        pykrx.stock.get_market_ohlcv_by_date(
            fromdate=fromdate,
            todate=todate,
            ticker='000660'  # SK 하이닉스
        ),
        pykrx.stock.get_market_ohlcv_by_date(
            fromdate=fromdate,
            todate=todate,
            ticker='005380'  # 현대차
        )
    ]

    length = 0
    for df in big_stocks:
        if length == 0:
            length = df.index.size
            continue

        assert length == df.index.size, 'Something is wrong with the big stocks.'

    # noinspection PyUnresolvedReferences
    return [d.date() for d in big_stocks[0].index]


business_days = _business_days()


def get_latest_business_date() -> date:
    return business_days[-1]


def normalize(code: str):
    return code[-6:]


class CandlesUpdater(abc.ABC):

    @abc.abstractmethod
    def update(self, stock):
        pass


class DayCandlesUpdater(CandlesUpdater):

    def __init__(self, days=365 * 3):
        self.begin = date.today() - timedelta(days=days)
        self.end = date.today()
        super().__init__()

    def update(self, stock):
        code = normalize(stock.code)
        # check if already exists
        with db.day_candles.DayCandleDynamicTable(normalize(code)) as table:
            if table.exists(date=latest_business_date):
                # up-to-date
                logging.info(f'{code}: up-to-date')
            else:
                logging.info(f'{code}: will be update')
                candles = charts.request_by_term(
                    code=code,
                    chart_type=charts.ChartType.DAY,
                    begin=self.begin,
                    end=self.end
                )

                rows = {}
                for candle in candles:
                    row = db.day_candles.DayCandle(
                        date=candle.date,
                        open=candle.open,
                        close=candle.close,
                        low=candle.low,
                        high=candle.high,
                        vol=candle.vol
                    )

                    if not table.exists(date=candle.date):
                        rows.update({candle.date: row})

                if rows:
                    logging.info(f'Inserting {len(rows)} candles for {self.begin} ~ {self.end}')
                    table.insert_all(list(rows.values()))


class MinuteCandlesUpdater(CandlesUpdater):

    def __init__(self, period=8, days=365 * 2):
        self.begin = date.today() - timedelta(days=days)
        self.end = date.today()
        self.stopped = False
        self.period = period
        super().__init__()

    def update(self, stock):
        code = normalize(stock.code)
        self.stopped = False

        # 차트 테이블 연결
        minute_table = db.minute_candles.MinuteCandleDynamicTable(code)
        day_table = db.day_candles.DayCandleDynamicTable(code)
        try:
            minute_table.open()
            day_table.open()

            end = None
            for begin in [d for d in business_days if self.begin <= d <= self.end]:
                if end and begin <= end:  # 직전 end 보다 begin 이 커질 때까지 스킵
                    continue

                if begin > self.end:
                    break

                end = begin + timedelta(days=self.period)
                if end > self.end:
                    end = self.end

                if day_table.exists(date=begin) and not minute_table.exists(date=begin):
                    candles = charts.request_by_term(
                        code=code,
                        chart_type=charts.ChartType.MINUTE,
                        begin=begin,
                        end=end
                    )

                    whitelist_dates = set([candle.date for candle in candles])
                    whitelist_dates = [d for d in whitelist_dates if not minute_table.exists(date=d)]

                    rows = {}
                    for candle in [candle for candle in candles if candle.date in whitelist_dates]:
                        row = db.minute_candles.MinuteCandle(
                            date=candle.date,
                            time=candle.time,
                            open=candle.open,
                            close=candle.close,
                            low=candle.low,
                            high=candle.high,
                            vol=candle.vol
                        )
                        rows.update({datetime.combine(date=candle.date, time=candle.time): row})

                    if rows:
                        logging.info(f'Inserting {len(rows)} candles...')
                        minute_table.insert_all(list(rows.values()))
        finally:
            minute_table.close()
            day_table.close()


class MinuteCandleValidator(MinuteCandlesUpdater):
    def __init__(self):
        super().__init__(period=1)


class Updater:

    def __init__(self):
        self.number = 0

    def update(self):
        with db.StockDynamicTable() as stock_table:
            all_stocks = stock_table.all()
            stock_table.insert_all(
                [
                    db.stocks.Stock(code=normalize(stock.code), name=stock.name) for stock in stocks.ALL_STOCKS
                    if normalize(stock.code) not in [stock.code for stock in all_stocks]
                ]
            )

            all_stocks = stock_table.all()

        def _update(stock):
            self.number += 1
            logging.info(f'{self.number} - {stock.name}({stock.code})')
            DayCandlesUpdater().update(stock)
            MinuteCandlesUpdater().update(stock)

        with ThreadPool(5) as pool:
            pool.map(_update, all_stocks)


def main():
    Updater().update()


if __name__ == '__main__':
    latest_business_date = get_latest_business_date()
    main()
