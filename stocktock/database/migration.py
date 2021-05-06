# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from multiprocessing.pool import ThreadPool

from database import charts as new
from database.candles import day_candles as old_day_candles
from database.candles import minute_candles as old_minute_candles
from database.stocks import all_stocks


def migrate_day_candles():
    def _migrate(code: str):
        with new.DayCandlesTable() as new_table:
            with old_day_candles.DayCandleTable(code) as old_table:
                candles = [
                    new.DayCandle(
                        code,
                        **{k: candle.__dict__.get(k)
                           for k in candle.__dict__.keys() if not k.startswith('_')})
                    for candle in old_table.all()
                ]

                new_table.insert_all(candles)

    with ThreadPool(5) as pool:
        pool.map(_migrate, [stock.code for stock in all_stocks()])


def migrate_minute_candles():
    for stock in all_stocks():
        code = stock.code
        with old_minute_candles.MinuteCandleTable(code) as old_table:
            candles = [
                new.MinuteCandle(
                    code,
                    **{k: candle.__dict__.get(k)
                       for k in candle.__dict__.keys() if not k.startswith('_')})
                for candle in old_table.all()
            ]

            candles_by_date = {}
            for candle in candles:
                if candle.date not in candles_by_date:
                    candles_by_date.update({candle.date: []})

                candles_by_date.get(candle.date).append(candle)

            def _migrate(d):
                print(1, end='')
                with new.MinuteCandlesTable(d) as new_table:
                    if not new_table.exists(code=code):
                        try:
                            print(1, end='')
                            new_table.insert_all(candles_by_date.get(d))
                        except:
                            pass

            with ThreadPool(5) as pool:
                pool.map(_migrate, candles_by_date.keys())


migrate_minute_candles()
