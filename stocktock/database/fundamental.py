from dataclasses import dataclass
from datetime import date, timedelta
from typing import *

import numpy as np
import psycopg2
from psycopg2.extensions import register_adapter
from pykrx import stock as pykrx_stock
from sqlalchemy import create_engine, Date, Float, Column, BigInteger, String, and_, extract

from config import config
from .common import AbstractDynamicTable

psycopg2.extensions.register_adapter(np.int64, psycopg2._psycopg.AsIs)


@dataclass
class Fundamental:
    date: date
    bps: float
    per: float
    pbr: float
    eps: float
    div: float
    dps: float


@dataclass
class Capital:
    code: str
    date: date
    cap: int


url = config.database.get_url('fundamentals')
engine = create_engine(url, client_encoding='utf-8')


class FundamentalTable(AbstractDynamicTable[Fundamental]):
    def __init__(self, code: str, create_if_not_exists: bool = False):
        columns = [
            Column('date', Date, primary_key=True),
            Column('bps', Float),
            Column('per', Float),
            Column('pbr', Float),
            Column('eps', Float),
            Column('div', Float),
            Column('dps', Float),
        ]

        super().__init__(engine, Fundamental, f'fundamentals_{code}', columns,
                         create_if_not_exists=create_if_not_exists)


class CapitalTable(AbstractDynamicTable[Capital]):
    def __init__(self, code: str, create_if_not_exists: bool = False):
        columns = [
            Column('date', Date, primary_key=True),
            Column('cap', BigInteger),
        ]

        super().__init__(engine, Capital, f'capitals_{code}', columns,
                         create_if_not_exists=create_if_not_exists)


class AllCapitalTable(AbstractDynamicTable[Capital]):
    def __init__(self, create_if_not_exists: bool = False):
        columns = [
            Column('code', String, primary_key=True),
            Column('date', Date, primary_key=True),
            Column('cap', BigInteger),
        ]

        super().__init__(engine, Capital, f'capitals', columns,
                         create_if_not_exists=create_if_not_exists)

    def find_all_at(self, at: date) -> List[Capital]:
        return self.query().filter(self.proxy.date == at).all()

    def find_all_in(self, begin: date, end: date, codes=None) -> List[Capital]:
        return self.query().filter(
            and_(
                begin <= self.proxy.date,
                self.proxy.date <= end,
                True if codes is None else self.proxy.code.in_(codes)
            )
        ).all()

    def find_all_by_year_and_month(self, year: int, month: int):
        return self.query().filter(
            and_(
                extract('year', self.proxy.date) == year,
                extract('month', self.proxy.date) == month,
            )
        ).all()


def _date_to_str(d: date):
    return d.strftime('%Y%m%d')


def _update_fundamentals(code: str, fromdate: date, todate: date):
    df = pykrx_stock.get_market_fundamental_by_date(
        fromdate=_date_to_str(fromdate),
        todate=_date_to_str(todate),
        ticker=code
    )

    funds = []
    for idx, row in df.iterrows():
        all_nan = True
        for v in row:
            if v:
                all_nan = False
                break

        if not all_nan:
            # noinspection PyUnresolvedReferences
            funds.append(
                Fundamental(
                    date=idx.date(),
                    bps=row.get('BPS'),
                    per=row.get('PER'),
                    pbr=row.get('PBR'),
                    eps=row.get('EPS'),
                    div=row.get('DIV'),
                    dps=row.get('DPS'),
                )
            )

    with FundamentalTable(code=code, create_if_not_exists=True) as fund_table:
        whitelist = []
        exists_rows = fund_table.all()
        for fund in funds:
            if fund.date not in [row.date for row in exists_rows]:
                whitelist.append(fund)

        print(f'Inserting {len(whitelist)} records...')
        fund_table.insert_all(whitelist)


def _update_capitals(code: str, fromdate: date, todate: date):
    df = pykrx_stock.get_market_cap_by_date(
        fromdate=_date_to_str(fromdate),
        todate=_date_to_str(todate),
        ticker=code
    )

    capitals = []
    for idx, row in df.iterrows():
        all_nan = True
        for v in row:
            if v:
                all_nan = False
                break

        if not all_nan:
            # noinspection PyUnresolvedReferences
            capitals.append(
                Capital(
                    code=code,
                    date=idx.date(),
                    cap=row.get('시가총액'),
                )
            )

    with AllCapitalTable() as cap_table:
        whitelist = []
        exists_rows = cap_table.all()
        for cap in capitals:
            if cap.date not in [row.date for row in exists_rows]:
                whitelist.append(cap)

        print(f'Inserting {len(whitelist)} records...')
        cap_table.insert_all(whitelist)


def find_all_codes(fromdate: date, todate: date):
    tempd = fromdate
    codes = {}
    while True:
        codes.update({code: None for code in pykrx_stock.get_market_ticker_list(_date_to_str(tempd), market='ALL')})

        if tempd > todate:
            break
        tempd += timedelta(days=365)

    for code in codes:
        name = pykrx_stock.get_market_ticker_name(code)
        if isinstance(name, str):
            codes.update({code: name})

    return codes


def integrate_capitals():
    codes = []
    with AllCapitalTable(create_if_not_exists=True) as all_capital_table:
        table_names = all_capital_table.inspector.get_table_names()
        for table_name in table_names:
            if table_name.startswith('capitals_'):
                code = table_name.split('_')[1]
                codes.append(code)

        for code in codes:
            with CapitalTable(code=code) as capital_table:
                all_capital_table.insert_all(
                    [Capital(code=code, date=capital.date, cap=capital.cap) for capital in capital_table.all()]
                )


def udpate_all():
    fromdate = date(2021, 7, 15)
    todate = date.today()
    codes = find_all_codes(fromdate, todate)

    total = [code for code, name in codes.items() if name]
    num = 0
    for code in [code for code, name in codes.items() if name]:
        num += 1
        print(f'{num}/{len(total)}')
        _update_fundamentals(code, fromdate=fromdate, todate=todate)
        _update_capitals(code, fromdate=fromdate, todate=todate)
