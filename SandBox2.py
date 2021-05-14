import logging
from datetime import date, timedelta

import database.charts
from utils import log

log.init()


def main():
    begin = date.today() - timedelta(days=365 * 2)
    end = date.today()

    for i in range((end - begin).days + 1):
        d = begin + timedelta(days=i)
        with database.charts.DayCandlesTable() as day_candles_table:
            day_candles = day_candles_table.find_by_date(d)

        for day_candle in day_candles:
            code = day_candle.code
            with database.charts.MinuteCandlesTable(day_candle.date) as minute_candles_table:
                if minute_candles_table.is_table_exists():
                    logging.warning(f'{day_candle.date} table for minute candles not exists.')
                    break
                else:
                    minute_candles = minute_candles_table.find_all(codes=[day_candle.code])
                    date_str = day_candle.date.strftime('%Y%m%d')
                    if not minute_candles:
                        logging.warning(f'No candle of {code} at {date_str}')


if __name__ == '__main__':
    main()
