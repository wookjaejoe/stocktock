from pykrx import stock
from datetime import date
from typing import *


def kospi_n_codes(at: date, n: int) -> List[str]:
    return [cap[0] for cap in stock.get_market_cap_by_ticker(date=at.strftime('%Y%m%d')).iterrows()][:n]
