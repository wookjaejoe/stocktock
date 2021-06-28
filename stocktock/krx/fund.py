from dataclasses import dataclass
from datetime import date
from enum import Enum, auto

from pykrx import stock


def __date_to_str(d: date): return d.strftime('%Y%m%d')


class Industry(Enum):
    NONE = auto()


@dataclass
class Fund:
    date: date
    bps: float
    per: float
    pbr: float
    eps: float
    div: float
    dps: float
    ind: Industry


def fetch_fund(code: str, fromdate: date, todate: date):
    df = stock.get_market_fundamental_by_date(
        fromdate=__date_to_str(fromdate),
        todate=__date_to_str(todate),
        ticker=code
    )
    for idx, row in df.iterrows():
        # noinspection PyUnresolvedReferences
        yield Fund(
            date=idx.date(),
            bps=row.get('BPS'),
            per=row.get('PER'),
            pbr=row.get('PBR'),
            eps=row.get('EPS'),
            div=row.get('DIV'),
            dps=row.get('DPS'),
            ind=Industry.NONE
        )
