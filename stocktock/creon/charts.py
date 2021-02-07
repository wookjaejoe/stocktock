from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from .com import *

KST = timezone(timedelta(hours=9))


class ChartType(Enum):
    DAY = ord('D')
    WEEK = ord('W')
    MONTH = ord('M')
    MINUTES = ord('m')
    TICK = ord('T')


@dataclass
class ChartData:
    code: str
    chart_type: ChartType
    datetime: datetime
    open: int
    high: int
    low: int
    close: int
    vol: int


@limit_safe(req_type=ReqType.NON_TRADE)
def request(code: str, chart_type: ChartType, count: int = -1) -> List[ChartData]:
    chart = stockchart()

    chart.SetInputValue(0, code)  # 종목코드
    chart.SetInputValue(1, ord('2'))  # 개수로 받기
    chart.SetInputValue(4, count)  # 조회 개수
    # 요청항목 - 날짜,시간,시가,고가,저가,종가,거래량
    chart.SetInputValue(5, [0, 1, 2, 3, 4, 5, 8])
    chart.SetInputValue(6, chart_type.value)  # '차트 주기 - 분/틱
    chart.SetInputValue(7, 1)  # 분틱차트 주기
    chart.SetInputValue(9, ord('1'))  # 수정주가 사용
    chart.BlockRequest()

    assert chart.GetDibStatus() == 0, chart.GetDibMsg1()
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

        try:
            dt = datetime.strptime(str(_date), '%Y%m%d %H%M%S', ).astimezone(KST)
        except:
            dt = datetime.strptime(str(_date), '%Y%m%d').astimezone(KST)

        data = ChartData(
            code=code,
            chart_type=chart_type,
            datetime=dt,
            open=_open,
            high=high,
            low=low,
            close=close,
            vol=vol
        )

        items.append(data)

    items.sort(key=lambda chart_data: chart_data.datetime)
    return items
