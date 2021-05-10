from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import *

from pykrx import stock


@dataclass
class Ohlcv:
    open: float
    high: float
    low: float
    close: float
    vol: float
    transaction: float


def date_to_str(d: date):
    return d.strftime('%Y%m%d')


def make_index_dict(d: date, market: str = None):
    if market:
        tickers = stock.get_index_ticker_list(date_to_str(d), market=market)
    else:
        tickers = stock.get_index_ticker_list(date_to_str(d))

    return {ticker: stock.get_index_ticker_name(ticker) for ticker in tickers}


def get_index_ohlcv(ticker: str, fromdate: date, todate: date) -> Dict[date, Ohlcv]:
    df = stock.get_index_ohlcv_by_date(
        ticker=ticker,
        fromdate=date_to_str(fromdate),
        todate=date_to_str(todate)
    )

    # check index changes
    expected_df_columns = ['시가', '고가', '저가', '종가', '거래량', '거래대금']
    for i in range(len(expected_df_columns)):
        assert df.columns[i] == expected_df_columns[i], f'Index changed: ({df.index[i]}, {expected_df_columns[i]})'

    # convert Dataframe to dict
    df_dict = df.to_dict(orient='index')

    # marshalling
    result = {}
    for timestamp in df_dict.keys():
        d = timestamp.date()
        values = list(df_dict.get(timestamp).values())
        result.update(
            {
                d: Ohlcv(
                    open=values[0],
                    high=values[1],
                    low=values[2],
                    close=values[3],
                    vol=values[4],
                    transaction=values[5],
                )}
        )

    return result


@dataclass
class Index:
    ticker: str
    name: str
    values: Dict[date, Ohlcv]


@dataclass
class InterestIndexes:
    # KOSPI
    kospi: Index
    kospi_50: Index
    kospi_100: Index
    kospi_200: Index

    # KOSDAQ
    kosdaq: Index
    kosdaq_150: Index

    # KRX
    krx_100: Index
    krx_300: Index

    @classmethod
    def _load_one(cls, ticker, fromdate: date, todate: date) -> Index:
        return Index(
            ticker=ticker,
            name=stock.get_index_ticker_name(ticker),
            values=get_index_ohlcv(ticker, fromdate, todate)
        )

    @classmethod
    def load(cls, fromdate: date, todate: date) -> InterestIndexes:
        indexes = InterestIndexes(
            kospi=cls._load_one('1001', fromdate, todate),
            kospi_50=cls._load_one('1035', fromdate, todate),
            kospi_100=cls._load_one('1034', fromdate, todate),
            kospi_200=cls._load_one('1028', fromdate, todate),

            kosdaq=cls._load_one('2001', fromdate, todate),
            kosdaq_150=cls._load_one('2203', fromdate, todate),

            krx_100=cls._load_one('5042', fromdate, todate),
            krx_300=cls._load_one('5300', fromdate, todate),
        )

        assert indexes.kospi.name == '코스피'
        assert indexes.kospi_50.name == '코스피 50'
        assert indexes.kospi_100.name == '코스피 100'
        assert indexes.kospi_200.name == '코스피 200'

        assert indexes.kosdaq.name == '코스닥'
        assert indexes.kosdaq_150.name == '코스닥 150'

        assert indexes.krx_100.name == 'KRX 100'
        assert indexes.krx_300.name == 'KRX 300'
        return indexes
