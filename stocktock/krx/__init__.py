from pykrx import stock
from datetime import date
from typing import *


def __date_to_str(d: date):
    return d.strftime('%Y%m%d')


def kospi_n_codes(at: date, n: int) -> List[str]:
    # noinspection PyTypeChecker
    return [cap[0] for cap in stock.get_market_cap_by_ticker(date=__date_to_str(at)).iterrows()][:n]


def is_business_day(at: date):
    business_days = [date(ts.year, ts.month, ts.day) for ts in
                     stock.get_previous_business_days(year=at.year, month=at.month)]
    return at in business_days
