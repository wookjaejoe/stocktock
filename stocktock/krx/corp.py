import pandas as pd
from datetime import date
from dateutil.parser import parse
from database import stocks
from dataclasses import dataclass


@dataclass
class Corp:
    code: str
    industry: str
    since: date


def update_stocks():
    df = pd.read_html('http://kind.krx.co.kr/corpgeneral/corpList.do?method=download', header=0)[0]
    corp_list = []
    for idx, row in df.iterrows():
        corp = Corp(
            code=str(row.get('종목코드')).zfill(6),
            industry=row.get('업종'),
            since=parse(row.get('상장일')).date()
        )
        corp_list.append(corp)

    with stocks.StockTable() as stock_table:
        for corp in corp_list:
            try:
                stock = stock_table.find(corp.code)
                stock.industry = corp.industry
                stock.since = corp.since
                print(stock)
            except:
                pass

        stock_table.session.commit()


update_stocks()
