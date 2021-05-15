import logging
from datetime import date, timedelta, datetime
from multiprocessing.pool import ThreadPool

import creon.charts
import creon.stocks
import database.charts
import database.stocks
from utils import log

log.init()


def normalize(code: str):
    return code[-6:]


def convert_market_type(market_type) -> database.stocks.Market:
    if market_type.name == 'KOSPI':
        return database.stocks.Market.KOSPI
    elif market_type.name == 'KOSDAQ':
        return database.stocks.Market.KOSDAQ

    raise RuntimeError(f'Not supported type: {market_type}')


def update_stocks():
    with database.stocks.StockTable() as stock_table:
        for creon_stock in creon.stocks.ALL_STOCKS:
            db_stock = stock_table.find(normalize(creon_stock.code))
            if db_stock:
                db_stock.name = creon_stock.name
                db_stock.market = convert_market_type(creon_stock.market_type)
            else:
                stock_table.insert(database.stocks.Stock(
                    code=normalize(creon_stock.code),
                    name=creon_stock.name,
                    market=convert_market_type(creon_stock.market_type)
                ))

        stock_table.session.commit()

    return stock_table.all()


def update_day_candles(code: str, begin: date, end: date):
    with database.charts.DayCandlesTable() as day_candles_table:
        candles = day_candles_table.find_all(codes=[code])
        creon_candles = creon.charts.request_by_term(
            code=code,
            chart_type=creon.charts.ChartType.DAY,
            begin=begin,
            end=end
        )

        inserts = []
        for creon_candle in creon_candles:

            # 중복 방어
            if creon_candle.date in [candle.date for candle in inserts]:
                continue

            if creon_candle.date not in [candle.date for candle in candles]:
                inserts.append(
                    database.charts.DayCandle(
                        code=normalize(creon_candle.code),
                        date=creon_candle.date,
                        open=creon_candle.open,
                        close=creon_candle.close,
                        low=creon_candle.low,
                        high=creon_candle.high,
                        vol=creon_candle.vol
                    )
                )

        day_candles_table.insert_all(inserts)


def update_minute_candles(code: str, begin: date, end: date):
    if begin > end:
        return

    creon_candles = creon.charts.request_by_term(
        code=code,
        chart_type=creon.charts.ChartType.MINUTE,
        begin=begin,
        end=end
    )

    creon_candles_by_date = {}
    for creon_candle in creon_candles:
        if creon_candle.date not in creon_candles_by_date:
            creon_candles_by_date.update({creon_candle.date: []})

        creon_candles_by_date.get(creon_candle.date).append(creon_candle)

    for d in [begin + timedelta(days=i) for i in range((end - begin).days + 1)]:
        creon_candles = creon_candles_by_date.get(d)
        if not creon_candles:
            continue

        with database.charts.MinuteCandlesTable(d, True) as minute_candles_table:
            exist_candles = minute_candles_table.find_all([code])
            exist_datetimes = [datetime.combine(candle.date, candle.time) for candle in exist_candles]

            new_candles = [database.charts.MinuteCandle(
                code=code,
                date=creon_candle.date,
                time=creon_candle.time,
                open=creon_candle.open,
                close=creon_candle.close,
                low=creon_candle.low,
                high=creon_candle.high,
                vol=creon_candle.vol
            ) for creon_candle in creon_candles if
                datetime.combine(creon_candle.date, creon_candle.time) not in exist_datetimes]

            if new_candles:
                print(code, d.strftime('%Y%m%d'))
                minute_candles_table.insert_all(new_candles)


def main():
    begin = date.today() - timedelta(days=400)
    end = date.today()

    def date_to_str(d: date):
        return d.strftime('%Y-%m-%d')

    logging.info(f'STARTED: {date_to_str(begin)} ~ {date_to_str(end)}')

    logging.info('Updating stocks...')
    stocks = update_stocks()

    def update(code: str):
        try:
            update_day_candles(code, begin, end)
            update_minute_candles(code, begin, end)
        except creon.stocks.StockNotFound:
            pass

    logging.info('Updating candles...')
    with ThreadPool(5) as pool:
        pool.map(update, [stock.code for stock in stocks])


if __name__ == '__main__':
    main()
