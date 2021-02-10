from __future__ import annotations

import logging
from dataclasses import dataclass

from retry import retry

from creon import mas
from .com import *


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

    arg_65: any
    arg_66: any
    arg_67: any
    arg_68: any


@dataclass
class StockDetailShort:
    code: str
    name: str
    margin: int
    margin_code: int  # 1: 상한, 2: 상승, 3: 보합, 4: 하한, 5: 하락, 6: 기세상한, 7: 기세상승, 8: 기세하한, 9: 기세하락
    current: int
    bid: int  # 매수호가
    ask: int  # 매도호가
    volumn: int  # 거래량
    market: int  # 장 구분 - '0': 동시호가와 장중이외의 시간, '1': 동시호가시간(예상체결가 들어오는 시간), '2': 장중
    expected_conclusion_price: int  # 예상 체결가
    expected_volumn: int  # 예상 체결 수량
    expected_conclusion_price_margin: int  # 예상 체결가 전일 대비


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
    _codemgr = codemgr()

    result = []
    for code in _codemgr.GetStockListByMarket(market_type.value):
        stock = Stock(
            market_type=market_type,
            code=code,
            secondCode=_codemgr.GetStockSectionKind(code),
            name=_codemgr.CodeToName(code),
            stdPrice=_codemgr.GetStockStdPrice(code)
        )

        result.append(stock)

    return result


ALL_STOCKS = get_all(MarketType.EXCHANGE) + get_all(MarketType.KOSDAQ)

_availables = None


def get_availables() -> List[str]:
    """
    임시 코드 - 시가 총액 2000억 ~ 10000억
    """
    global _availables
    if _availables:
        return _availables

    # 찌꺼기 필터링
    logging.info('Filtering trashes...')
    available_codes = [stock.code for stock in ALL_STOCKS if
                       get_status(stock.code) == 0 and
                       get_supervision(stock.code) == 0 and
                       get_control_kind(stock.code) == 0 and
                       get_stock_section_kind(stock.code) == SectionKind.CPC_KSE_SECTION_KIND_ST]

    # 시가 총액 기반 필터링
    logging.info('Filtering with capitalizations...')
    available_codes = [detail.code for detail in get_details(available_codes) if
                       2000_0000_0000 < detail.capitalization() < 2_0000_0000_0000]

    # 디테일 생성
    logging.info(f'Make details for {len(available_codes)} stocks...')
    details: Dict[str, StockDetail2] = {
        detail.code: detail
        for detail in get_details(available_codes)
    }

    # 정배열 필터링
    logging.info(f'Filtering with straighhts...')
    straights = []
    for code, detail in details.items():
        calculator = mas.get_calculator(detail.code)
        if calculator.is_straight():
            straights.append(code)

    _availables = straights
    logging.info(f'Finished filtering - final availables: {len(_availables)}')
    return _availables


def get_name(code: str):
    _stockcode = stockcode()

    for stock in ALL_STOCKS:
        if code == stock.code:
            return stock.name

    return _stockcode.CodeToName(code)


def is_kos(code):
    """
    Is kospi | kosdaq?
    """
    for stock in ALL_STOCKS:
        if code == stock.code:
            return True

    return False


@retry(tries=3, delay=5)
@limit_safe(ReqType.NON_TRADE)
def get_detail(code: str) -> StockDetail:
    _stockmst = stockmst()

    # 현재가 객체 구하기
    _stockmst.SetInputValue(0, code)
    _stockmst.BlockRequest()
    req_status = _stockmst.GetDibStatus()
    req_msg = _stockmst.GetDibMsg1()
    assert req_status == 0, f'Request Failure: ({req_status}) {req_msg}'

    try:
        exFlag = ExpectedFlag(_stockmst.GetHeaderValue(58))
    except:
        exFlag = None

    # todo: 헤더 훨씬 많음
    # http://cybosplus.github.io/cpdib_rtf_1_/stockmst.htm
    return StockDetail(
        # 현재가 정보 조회
        code=_stockmst.GetHeaderValue(0),  # 종목코드
        name=_stockmst.GetHeaderValue(1),  # 종목명
        time=_stockmst.GetHeaderValue(4),  # 시간
        cprice=_stockmst.GetHeaderValue(11),  # 종가
        diff=_stockmst.GetHeaderValue(12),  # 대비
        open=_stockmst.GetHeaderValue(13),  # 시가
        high=_stockmst.GetHeaderValue(14),  # 고가
        low=_stockmst.GetHeaderValue(15),  # 저가
        offer=_stockmst.GetHeaderValue(16),  # 매도호가 - 셀러가 팔고 싶은 가격
        bid=_stockmst.GetHeaderValue(17),  # 매수호가 - 구매자가 사고 싶은 가격
        vol=_stockmst.GetHeaderValue(18),  # 거래량
        vol_value=_stockmst.GetHeaderValue(19),  # 거래대금

        # 예상 체결관련 정보
        exFlag=exFlag,  # 예상체결가 구분 플래그
        exPrice=_stockmst.GetHeaderValue(55),  # 예상체결가
        exDiff=_stockmst.GetHeaderValue(56),  # 예상체결가 전일대비
        exVol=_stockmst.GetHeaderValue(57),  # 예상체결수량

        arg_65=_stockmst.GetHeaderValue(65),
        arg_66=_stockmst.GetHeaderValue(66),
        arg_67=_stockmst.GetHeaderValue(67),
        arg_68=_stockmst.GetHeaderValue(68),
    )


@dataclass
class StockDetail2:
    code: str  # 종목 코드
    name: str  # 종목명
    time: int  # 시간(HHMM)
    price: int  # 현재가
    margin: int  # 전일대비
    status: int  # 상태구분
    # '1': 상한
    # '2':상승
    # '3':보합
    # '4':하한
    # '5':하락
    # '6':기세상한
    # '7':기세상승
    # '8':기세하한
    # '9':기세하락

    open: int  # 시가
    high: int  # 고가
    low: int  # 저가
    ask: int  # 매도호가
    bid: int  # 매수호가
    volumn_week: int  # 거래량 [주의] 단위 1주
    transaction: int  # 거래대금 [주의] 단위 천원
    total_selling_balance: int  # 총매도잔량
    total_buying_balance: int  # 총매수잔량
    selling_balance: int  # 매도잔량
    buying_balance: int  # 매수잔량
    listed_stock_count: int  # 상장주식수
    foreign_ownership_ratio: int  # 외국인보유비율(%)
    yesterday_close: int  # 전일종가
    yesterday_volumn: int  # 전일거래량
    strength: int  # 체결강도
    field_22: int  # 순간체결량
    field_23: int  # 체결가비교 Flag
    # 'O':매도
    # 'B':매수

    field_24: int  # 호가비교 Flag
    # 'O':매도
    # 'B':매수

    field_25: int  # 동시호가구분
    # '1':동시호가
    # '2':장중

    field_26: int  # 예상체결가
    field_27: int  # 예상체결가 전일대비
    field_28: int  # 예상체결가 상태구분
    # '1':상한
    # '2':상승
    # '3':보합
    # '4':하한
    # '5':하락
    # '6':기세상한
    # '7':기세상승
    # '8':기세하한
    # '9':기세하락

    field_29: int  # 예상체결가 거래량

    def capitalization(self):
        return self.listed_stock_count * self.price


@limit_safe(req_type=ReqType.NON_TRADE)
def get_details(stock_codes: List[str]):
    def request(codes: List[str]):
        _stockmst2 = stockmst2()
        _stockmst2.SetInputValue(0, ','.join(codes))
        _stockmst2.BlockRequest()
        count = _stockmst2.GetHeaderValue(0)
        result = []
        for i in range(count):
            result.append(StockDetail2(
                code=_stockmst2.GetDataValue(0, i),
                name=_stockmst2.GetDataValue(1, i),
                time=_stockmst2.GetDataValue(2, i),
                price=_stockmst2.GetDataValue(3, i),
                margin=_stockmst2.GetDataValue(4, i),
                status=_stockmst2.GetDataValue(5, i),
                open=_stockmst2.GetDataValue(6, i),
                high=_stockmst2.GetDataValue(7, i),
                low=_stockmst2.GetDataValue(8, i),
                ask=_stockmst2.GetDataValue(9, i),
                bid=_stockmst2.GetDataValue(10, i),
                volumn_week=_stockmst2.GetDataValue(11, i),
                transaction=_stockmst2.GetDataValue(12, i),
                total_selling_balance=_stockmst2.GetDataValue(13, i),
                total_buying_balance=_stockmst2.GetDataValue(14, i),
                selling_balance=_stockmst2.GetDataValue(15, i),
                buying_balance=_stockmst2.GetDataValue(16, i),
                listed_stock_count=_stockmst2.GetDataValue(17, i),
                foreign_ownership_ratio=_stockmst2.GetDataValue(18, i),
                yesterday_close=_stockmst2.GetDataValue(19, i),
                yesterday_volumn=_stockmst2.GetDataValue(20, i),
                strength=_stockmst2.GetDataValue(21, i),
                field_22=_stockmst2.GetDataValue(22, i),
                field_23=_stockmst2.GetDataValue(23, i),
                field_24=_stockmst2.GetDataValue(24, i),
                field_25=_stockmst2.GetDataValue(25, i),
                field_26=_stockmst2.GetDataValue(26, i),
                field_27=_stockmst2.GetDataValue(27, i),
                field_28=_stockmst2.GetDataValue(28, i),
                field_29=_stockmst2.GetDataValue(29, i),
            ))

        return result

    stock_codes = stock_codes.copy()
    while stock_codes:
        req_limit = 110
        partial_codes = []
        for _ in range(req_limit):
            if stock_codes:
                partial_codes.append(stock_codes.pop())
            else:
                break

        for detail in request(partial_codes):
            yield detail


def get_yesterday_close(code: str):
    return codemgr().GetStockYdClosePrice(code)


@limit_safe(ReqType.NON_TRADE)
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


def get_supervision(code: str):
    """
    0: 일반종목
    1: 관리
    """
    return codemgr().GetStockSupervisionKind(code)


def get_status(code: str):
    """
    0: 정상
    1: 거래정지
    2: 거래중단
    """
    return codemgr().GetStockStatusKind(code)


def get_capital_type(code: str):
    """
    0: 제외
    1: 대
    2: 중
    3: 소
    """
    return codemgr().GetStockCapital(code)


class SectionKind(Enum):
    CPC_KSE_SECTION_KIND_NULL = 0  # 구분없음
    CPC_KSE_SECTION_KIND_ST = 1  # 주권
    CPC_KSE_SECTION_KIND_MF = 2  # 투자회사
    CPC_KSE_SECTION_KIND_RT = 3  # 부동산투자회사
    CPC_KSE_SECTION_KIND_SC = 4  # 선박투자회사
    CPC_KSE_SECTION_KIND_IF = 5  # 사회간접자본투융자회사
    CPC_KSE_SECTION_KIND_DR = 6  # 주식예탁증서
    CPC_KSE_SECTION_KIND_SW = 7  # 신수인수권증권
    CPC_KSE_SECTION_KIND_SR = 8  # 신주인수권증서
    CPC_KSE_SECTION_KIND_ELW = 9  # 주식워런트증권
    CPC_KSE_SECTION_KIND_ETF = 10  # 상장지수펀드(ETF)
    CPC_KSE_SECTION_KIND_BC = 11  # 수익증권
    CPC_KSE_SECTION_KIND_FETF = 12  # 해외ETF
    CPC_KSE_SECTION_KIND_FOREIGN = 13  # 외국주권
    CPC_KSE_SECTION_KIND_FU = 14  # 선물
    CPC_KSE_SECTION_KIND_OP = 15  # 옵션


def get_stock_section_kind(code: str) -> Optional[SectionKind]:
    try:
        return SectionKind(codemgr().GetStockSectionKind(code))
    except:
        pass


def get_control_kind(code: str):
    """
    [helpstring("정상")]    CPC_CONTROL_NONE           = 0,
    [helpstring("주의")]    CPC_CONTROL_ATTENTION      = 1,
    [helpstring("경고")]    CPC_CONTROL_WARNING        = 2,
    [helpstring("위험예고")] CPC_CONTROL_DANGER_NOTICE  = 3,
    [helpstring("위험")]    CPC_CONTROL_DANGER         = 4,
    """
    return codemgr().GetStockControlKind(code)
