from dataclasses import dataclass
from enum import Enum
from typing import *

from .com import *


# todo: 방어 with request retry

class MarketType(Enum):
    EXCHANGE = 1  # 거래소
    KOSDAQ = 2  # 코스닥


@dataclass
class Stock:
    market_type: MarketType
    code: str
    secondCode: int
    name: str
    stdPrice: int


@dataclass
class ExpectedFlag(Enum):
    """
    장 구분
    """
    A = ord('0')  # 동시호가와 장중 이외의 시간
    B = ord('1')  # 동시호가 시간
    C = ord('2')  # 장중 또는 장종료


@dataclass
class StockDetail:
    # 현재가 정보 조회
    code: any  # 종목코드
    name: any  # 종목명
    time: any  # 시간
    cprice: any  # 종가
    diff: any  # 대비
    open: any  # 시가
    high: any  # 고가
    low: any  # 저가
    offer: any  # 매도호가
    bid: any  # 매수호가
    vol: any  # 거래량
    vol_value: any  # 거래대금

    # 예상 체결관련 정보
    exFlag: ExpectedFlag  # 예상체결가 구분 플래그
    exPrice: any  # 예상체결가
    exDiff: any  # 예상체결가 전일대비
    exVol: any  # 예상체결수량


@dataclass
class StockTrend:
    date: any  # 일자
    open_: any  # 시가
    high: any  # 고가
    low: any  # 저가
    close: any  # 종가
    diff: any  # ?
    vol: any  # ?


def get_all(market_type: MarketType) -> List[Stock]:
    result = []
    for code in codemgr.GetStockListByMarket(market_type.value):
        stock = Stock(
            market_type=market_type,
            code=code,
            secondCode=codemgr.GetStockSectionKind(code),
            name=codemgr.CodeToName(code),
            stdPrice=codemgr.GetStockStdPrice(code)
        )

        result.append(stock)

    return result


def get_detail(code: str) -> StockDetail:
    # 현재가 객체 구하기
    stockmst.SetInputValue(0, code)  # 종목 코드 - 삼성전자
    stockmst.BlockRequest()
    req_status = stockmst.GetDibStatus()
    req_msg = stockmst.GetDibMsg1()
    assert req_status == 0, f'Request Failure: ({req_status}) {req_msg}'

    # todo: 헤더 훨씬 많음
    # http://cybosplus.github.io/cpdib_rtf_1_/stockmst.htm
    return StockDetail(
        # 현재가 정보 조회
        code=stockmst.GetHeaderValue(0),  # 종목코드
        name=stockmst.GetHeaderValue(1),  # 종목명
        time=stockmst.GetHeaderValue(4),  # 시간
        cprice=stockmst.GetHeaderValue(11),  # 종가
        diff=stockmst.GetHeaderValue(12),  # 대비
        open=stockmst.GetHeaderValue(13),  # 시가
        high=stockmst.GetHeaderValue(14),  # 고가
        low=stockmst.GetHeaderValue(15),  # 저가
        offer=stockmst.GetHeaderValue(16),  # 매도호가
        bid=stockmst.GetHeaderValue(17),  # 매수호가
        vol=stockmst.GetHeaderValue(18),  # 거래량
        vol_value=stockmst.GetHeaderValue(19),  # 거래대금

        # 예상 체결관련 정보
        exFlag=ExpectedFlag(stockmst.GetHeaderValue(58)),  # 예상체결가 구분 플래그
        exPrice=stockmst.GetHeaderValue(55),  # 예상체결가
        exDiff=stockmst.GetHeaderValue(56),  # 예상체결가 전일대비
        exVol=stockmst.GetHeaderValue(57),  # 예상체결수량
    )


def get_trend(code: str) -> Generator[StockTrend, None, None]:
    stockweek = win32com.client.Dispatch("DsCbo1.StockWeek")
    stockweek.SetInputValue(0, code)
    stockweek.BlockRequest()

    req_status = stockweek.GetDibStatus()
    req_msg = stockweek.GetDibMsg1()
    assert req_status == 0, f'Request Failure: ({req_status}) {req_msg}'

    # 일자별 정보 데이터 처리
    count = stockweek.GetHeaderValue(1)  # 데이터 개수
    for i in range(count):
        yield StockTrend(
            date=stockweek.GetDataValue(0, i),  # 일자
            open_=stockweek.GetDataValue(1, i),  # 시가
            high=stockweek.GetDataValue(2, i),  # 고가
            low=stockweek.GetDataValue(3, i),  # 저가
            close=stockweek.GetDataValue(4, i),  # 종가
            diff=stockweek.GetDataValue(5, i),  # ?
            vol=stockweek.GetDataValue(6, i),  # ?
        )


class CpEvent:
    """
    https://money2.creontrade.com/e5/mboard/ptype_basic/plusPDS/DW_Basic_Read.aspx?boardseq=299&seq=43&page=3&searchString=&prd=&lang=7&p=8833&v=8639&m=9505
    """

    def __init__(self, stockcur, on_received):
        self.stockcur = stockcur
        self.on_received = on_received

    # noinspection PyPep8Naming
    def OnReceived(self):
        time = self.stockcur.GetHeaderValue(3)  # 시간
        timess = self.stockcur.GetHeaderValue(18)  # 초
        ex_flag = self.stockcur.GetHeaderValue(19)  # 예상체결 플래그
        cprice = self.stockcur.GetHeaderValue(13)  # 현재가
        diff = self.stockcur.GetHeaderValue(2)  # 대비
        c_vol = self.stockcur.GetHeaderValue(17)  # 순간체결수량
        vol = self.stockcur.GetHeaderValue(9)  # 거래량

        if ex_flag == ord('1'):  # 동시호가 시간 (예상체결)
            print("실시간(예상체결)", time, timess, "*", cprice, "대비", diff, "체결량", c_vol, "거래량", vol)
        elif ex_flag == ord('2'):  # 장중(체결)
            print("실시간(장중체결)", time, timess, cprice, "대비", diff, "체결량", c_vol, "거래량", vol)

        self.on_received(time, timess, ex_flag, cprice, diff, c_vol, vol)

class StockSubscriber:
    """
    https://money2.creontrade.com/e5/mboard/ptype_basic/plusPDS/DW_Basic_Read.aspx?boardseq=299&seq=43&page=3&searchString=&prd=&lang=7&p=8833&v=8639&m=9505
    """

    def __init__(self, code):
        self.code = code
        # todo: StockCur 싱글톤인지 알아야함. 싱글톤일 경우 unsubscribe 시 모든 구독이 해제됨. 싱글톤 아닌것 같긴하다
        self.stockcur = new_stockcur()

    def subscribe(self, on_received):
        handler  = win32com.client.WithEvents(self.stockcur, CpEvent(self.stockcur, on_received))
        self.stockcur.SetInputValue(0, self.code)
        handler.set_params(self.stockcur)
        self.stockcur.Subscribe()

    def unsubscribe(self):
        self.stockcur.Unsubscribe()
