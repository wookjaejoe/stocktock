import threading
import time
from dataclasses import dataclass
from datetime import datetime
from queue import Queue
from typing import *
from uuid import uuid4, UUID

import schedule
import win32com.client

from database import DbManager
from utils.jsoner import JsonSerializable, deserialize

CATEGORIES = {
    1: '종목뉴스',
    2: '공시정보',
    10: '외국계 증권사 창구 첫 매수',
    11: '외국계 증권사 창구 첫 매도',
    12: '외국인 순매수',
    13: '외국인 순매도',
    21: '전일 거래량 갱신',
    22: '최근5일 거래량최고 갱신',
    23: '최근5일 매물대 돌파',
    24: '최근60일 매물대 돌파',
    28: '최근5일 첫 상한가',
    29: '최근5일 신고가 갱신',
    30: '최근5일 신저가 갱신',
    31: '상한가 직전',
    32: '하한가 직전',
    41: '주가 5MA 상향 돌파',
    42: '주가 5MA 하향 돌파',
    43: '거래량 5MA 상향 돌파',
    44: '주가 데드크로스(5MA < 20MA)',
    45: '주가 골든크로스(5MA > 20MA)',
    46: 'MACD 매수-Signal(9) 상향돌파',
    47: 'MACD 매도-Signal(9) 하향돌파',
    48: 'CCI 매수-기준선(-100) 상향돌파',
    49: 'CCI 매도-기준선(100) 하향돌파',
    50: 'Stochastic(10,5,5)매수- 기준선 상향돌파',
    51: 'Stochastic(10,5,5)매도- 기준선 하향돌파',
    52: 'Stochastic(10,5,5)매수- %K%D 교차',
    53: 'Stochastic(10,5,5)매도- %K%D 교차',
    54: 'Sonar 매수-Signal(9) 상향돌파',
    55: 'Sonar 매도-Signal(9) 하향돌파',
    56: 'Momentum 매수-기준선(100) 상향돌파',
    57: 'Momentum 매도-기준선(100) 하향돌파',
    58: 'RSI(14) 매수-Signal(9) 상향돌파',
    59: 'RSI(14) 매도-Signal(9) 하향돌파',
    60: 'Volume Oscillator 매수-Signal(9) 상향돌파',
    61: 'Volume Oscillator 매도-Signal(9) 하향돌파',
    62: 'Price roc 매수-Signal(9) 상향돌파',
    63: 'Price roc 매도-Signal(9) 하향돌파',
    64: '일목균형표 매수-전환선 > 기준선 상향교차',
    65: '일목균형표 매도-전환선 < 기준선 하향교차',
    66: '일목균형표 매수-주가가 선행스팬 상향돌파',
    67: '일목균형표 매도-주가가 선행스팬 하향돌파',
    68: '삼선전환도-양전환',
    69: '삼선전환도-음전환',
    70: '캔들패턴-상승반전형',
    71: '캔들패턴-하락반전형',
    81: '단기급락 후 5MA 상향돌파',
    82: '주가 이동평균밀집-5%이내',
    83: '눌림목 재 상승-20MA 지지',
}


@dataclass
class MarketEvent(JsonSerializable):
    _id: UUID = None
    datetime: datetime = None  # 시간
    code: str = None  # 종목 코드
    name: str = None  # 종목명
    category: int = None  # 항목 구분
    category_name: str = None  # 항목 구분 이름
    contents: str = None  # 내용

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash((self.code, self.name, self.category, self.contents))


def get_events():
    client = win32com.client.Dispatch('CpSysDib.CpMarketWatch')
    client.SetInputValue(0, '*')  # 모든 종목
    client.SetInputValue(1, '*')  # 모든 항목
    client.SetInputValue(2, 0)  # 시작시간: 처음부터
    client.BlockRequest()
    count = client.GetHeaderValue(2)  # 수신개수(short)
    events = []
    for i in range(count):
        now = datetime.now()

        def convert_datetime(dt: int):
            hour = int(dt / 100)
            minute = dt % 100

            return datetime(year=now.year,
                            month=now.month,
                            day=now.day - 1 if dt > now.hour * 100 + now.minute else now.day,
                            hour=hour,
                            minute=minute,
                            second=0)

        category = client.GetDataValue(3, i)
        evt = MarketEvent(
            _id=uuid4(),
            datetime=convert_datetime(client.GetDataValue(0, i)),
            code=client.GetDataValue(1, i),
            name=client.GetDataValue(2, i),
            category=category,
            category_name=CATEGORIES.get(category),
            contents=client.GetDataValue(4, i)
        )

        events.append(evt)

    return events


class EventBroker:
    CACHE_SIZE = 1000
    REQ_INTERVAL = 10

    def __init__(self):
        self.cache = Queue(maxsize=self.CACHE_SIZE)
        self.subscribers: List[Callable[[List[MarketEvent]], None]] = []
        self.stopped = True

        for event in DbManager.get_events().find().limit(self.CACHE_SIZE):
            event = deserialize(event, MarketEvent)
            self.cache.put(event)

    def collect(self):
        event_list = [evt for evt in get_events() if evt not in self.cache.queue]
        if not event_list:
            return

        # update cache
        for evt in event_list:
            self.cache.put(evt)

        # update db
        DbManager.get_events().insert_many([evt.__dict__ for evt in event_list])

        # run subscribers
        for subscriber in self.subscribers:
            subscriber(event_list)

    def start(self):
        self.collect()
        schedule.every(EventBroker.REQ_INTERVAL).seconds.do(self.collect)
        self.stopped = False
        while not self.stopped:
            schedule.run_pending()
            time.sleep(1)

    def start_async(self):
        threading.Thread(target=self.start).start()

    def stop(self):
        self.stopped = True

    def subscribe(self, func: Callable[[List[MarketEvent]], None]):
        self.subscribers.append(func)
