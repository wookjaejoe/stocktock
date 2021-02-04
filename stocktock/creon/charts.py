from dataclasses import dataclass
from datetime import datetime, date

from .com import *


class ChartType(Enum):
    DAY = ord('D')
    WEEK = ord('W')
    MONTH = ord('M')
    MINUTES = ord('m')
    TICK = ord('T')


class ChartDataField(Enum):
    date = 0
    time = 1
    open = 2
    high = 3
    low = 4
    close = 5
    vol = 8


@dataclass
class ChartData:
    date: int
    time: int
    open: int
    high: int
    low: int
    close: int
    vol: int


@dataclass(init=False)
class ChartDataEx(ChartData):
    dt: datetime

    def __init__(self):
        pass

    @classmethod
    def extend(cls, data: ChartData):
        result = ChartDataEx()
        result.__dict__ = data.__dict__.copy()
        result.dt = datetime(
            year=int(data.date / 10000),
            month=int(data.date / 10000 / 100),
            day=int(data.date / 10000) % 100,
            hour=int(data.time / 100),
            minute=data.time % 100
        )

        return result


def date_to_int(d: date):
    return int(d.strftime('%Y%m%d'))


def request(arguments: Dict[int, Any]) -> List[Dict[str, Any]]:
    for idx, value in arguments.items():
        stockchart().SetInputValue(idx, value)

    stockchart().BlockRequest()

    result = []
    output_names = stockchart().GetHeaderValue(2)  # 데이터 필드명
    output_length = stockchart().GetHeaderValue(3)  # 수신 개수
    for i in range(output_length):
        result.append({output_names[j]: stockchart().GetDataValue(j, i) for j in range(len(output_names))})

    return result


def request_by_term(code,
                    chart_type: ChartType,
                    begin: datetime,
                    end: datetime = datetime.now()):
    return request({
        0: code,  # 종목코드
        1: ord('1'),  # 기간으로 지정
        2: date_to_int(end),
        3: date_to_int(begin),
        5: [field.value for field in ChartDataField],  # 요청 필드
        6: chart_type.value,  # 차트 주기
        9: ord('1')  # 수정주가 사용
    })


def request_by_count(code,
                     chart_type: ChartType,
                     count=-1):
    return request({
        0: code,  # 종목코드
        1: ord('2'),  # 개수로 지정
        4: count,
        5: [field.value for field in ChartDataField],  # 요청 필드
        6: chart_type.value,  # 차트 주기
        9: ord('1')  # 수정주가 사용
    })
