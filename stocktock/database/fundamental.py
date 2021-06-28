from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import create_engine, Date, Float, Column

from config import config
from .common import AbstractDynamicTable


@dataclass
class Fundamental:
    date: date
    bps: float
    per: float
    pbr: float
    eps: float
    div: float
    dps: float


url = config.database.get_url('funds')
engine = create_engine(url, client_encoding='utf-8')


class FundamentalTable(AbstractDynamicTable[Fundamental]):
    def __init__(self, code: str, create_if_not_exists: bool):
        columns = [
            Column('date', Date, primary_key=True),
            Column('bps', Float),
            Column('per', Float),
            Column('pbr', Float),
            Column('eps', Float),
            Column('div', Float),
            Column('dps', Float),
        ]

        super().__init__(engine, Fundamental, f'funds_{code}', columns, create_if_not_exists=create_if_not_exists)


def _update(code: str, fromdate: date, todate: date):
    def __date_to_str(d: date):
        return d.strftime('%Y%m%d')

    from pykrx import stock as pykrx_stock
    try:
        df = pykrx_stock.get_market_fundamental_by_date(
            fromdate=__date_to_str(fromdate),
            todate=__date_to_str(todate),
            ticker=code
        )
    except:
        return

    funds = []
    for idx, row in df.iterrows():
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


def udpate_all():
    from .stocks import all_stocks
    for stock in all_stocks():
        print(stock)
        _update(stock.code, fromdate=date.today() - timedelta(days=365 * 5), todate=date.today())
