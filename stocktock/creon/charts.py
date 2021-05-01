from datetime import datetime, timezone, timedelta, date

from model import Candle
from .com import *
from .stocks import find
from .exceptions import CreonRequestError

KST = timezone(timedelta(hours=9))


class ChartType(Enum):
    DAY = ord('D')
    WEEK = ord('W')
    MONTH = ord('M')
    MINUTE = ord('m')
    TICK = ord('T')

    @classmethod
    def create_by_name(cls, name):
        for chart_type in ChartType:
            if chart_type.name == name:
                return chart_type


# noinspection DuplicatedCode
@limit_safe(req_type=ReqType.NON_TRADE)
def request_by_term(code: str, chart_type: ChartType, begin: date, end: date, period=1):
    assert end - begin <= timedelta(days=8), f'The period limit exceeded.'
    code = find(code).code
    chart = stockchart()
    chart.SetInputValue(0, code)  # 종목코드
    chart.SetInputValue(1, ord('1'))  # 개수로 받기
    chart.SetInputValue(2, int(end.strftime('%Y%m%d')))  # 요청 종료일
    chart.SetInputValue(3, int(begin.strftime('%Y%m%d')))  # 요청 종료일
    chart.SetInputValue(5, [0, 1, 2, 3, 4, 5, 8])
    chart.SetInputValue(6, chart_type.value)  # '차트 주기 - 분/틱
    chart.SetInputValue(7, period)  # '차트 주기 - 분/틱
    chart.SetInputValue(9, ord('1'))  # 수정주가 사용

    try:
        chart.BlockRequest()
    except Exception as e:
        raise CreonRequestError(str(e))

    CreonRequestError.check(chart)

    count = chart.GetHeaderValue(3)
    items = []
    for i in range(count):
        _date = chart.GetDataValue(0, i)  # 날짜
        _time = chart.GetDataValue(1, i)  # 시간
        _open = chart.GetDataValue(2, i)  # 시가
        high = chart.GetDataValue(3, i)  # 고가
        low = chart.GetDataValue(4, i)  # 저가
        close = chart.GetDataValue(5, i)  # 종가
        vol = chart.GetDataValue(6, i)  # 거래량
        _date = datetime.strptime(str(_date), '%Y%m%d').date()
        try:
            _time = datetime.strptime(str(_time), '%H%M').time()
        except:
            _time = datetime.strptime('0000', '%H%M').time()

        data = Candle(
            code=code,
            date=_date,
            time=_time,
            open=_open,
            high=high,
            low=low,
            close=close,
            vol=vol
        )

        items.append(data)

    items.sort(key=lambda candle: datetime.combine(candle.date, candle.time))
    return items


# noinspection DuplicatedCode
@limit_safe(req_type=ReqType.NON_TRADE)
def request(code: str, chart_type: ChartType, count: int = -1) -> List[Candle]:
    code = find(code).code
    chart = stockchart()
    chart.SetInputValue(0, code)  # 종목코드
    chart.SetInputValue(1, ord('2'))  # 개수로 받기
    chart.SetInputValue(4, count)  # 조회 개수
    # 요청항목 - 날짜,시간,시가,고가,저가,종가,거래량
    chart.SetInputValue(5, [0, 1, 2, 3, 4, 5, 8])
    chart.SetInputValue(6, chart_type.value)  # '차트 주기 - 분/틱
    chart.SetInputValue(7, 1)  # 분틱차트 주기
    chart.SetInputValue(9, ord('1'))  # 수정주가 사용

    try:
        chart.BlockRequest()
    except Exception as e:
        raise CreonRequestError(str(e))

    CreonRequestError.check(chart)

    count = chart.GetHeaderValue(3)
    items = []
    for i in range(count):
        _date = chart.GetDataValue(0, i)  # 날짜
        _time = chart.GetDataValue(1, i)  # 시간
        _open = chart.GetDataValue(2, i)  # 시가
        high = chart.GetDataValue(3, i)  # 고가
        low = chart.GetDataValue(4, i)  # 저가
        close = chart.GetDataValue(5, i)  # 종가
        vol = chart.GetDataValue(6, i)  # 거래량

        _date = datetime.strptime(str(_date), '%Y%m%d').date()
        try:
            _time = datetime.strptime(str(_time), '%H%M').time()
        except:
            _time = datetime.strptime('0000', '%H%M').time()

        data = Candle(
            code=code,
            date=_date,
            time=_time,
            open=_open,
            high=high,
            low=low,
            close=close,
            vol=vol
        )

        items.append(data)

    items.sort(key=lambda candle: datetime.combine(candle.date, candle.time))
    return items
