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


@dataclass
class EventCategory(JsonSerializable):
    _id: int = None
    name: str = None


@dataclass
class Event(JsonSerializable):
    _id: UUID = None
    datetime: datetime = None  # 시간
    code: str = None  # 종목 코드
    name: str = None  # 종목명
    category_id: int = None  # 항목 구분
    contents: str = None  # 내용

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash((self.code, self.name, self.category_id, self.contents))


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

        evt = Event(
            _id=uuid4(),
            datetime=convert_datetime(client.GetDataValue(0, i)),
            code=client.GetDataValue(1, i),
            name=client.GetDataValue(2, i),
            category_id=client.GetDataValue(3, i),
            contents=client.GetDataValue(4, i)
        )

        events.append(evt)

    return events


class EventBroker:
    CACHE_SIZE = 1000
    REQ_INTERVAL = 10

    def __init__(self):
        self.cache = Queue(maxsize=self.CACHE_SIZE)
        self.subscribers: List[Callable[[List[Event]], None]] = []
        self.stopped = True

        for event in DbManager.get_events().find().limit(self.CACHE_SIZE):
            event = deserialize(event, Event)
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

    def subscribe(self, func: Callable[[List[Event]], None]):
        self.subscribers.append(func)
