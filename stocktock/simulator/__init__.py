import abc
import threading
import time
from datetime import datetime, timedelta
from typing import *

from creon import charts


class Simulator:

    def __init__(self, begin: datetime, end: datetime, period: timedelta):
        self.begin = begin
        self.end = end
        self.period = period
        self.now = self.begin

    def start(self, callback):
        while self.now < self.end:
            callback(self.now)
            self.now += self.period


class DataProvider(abc.ABC):

    def __init__(self):
        self.stopped = False
        self.subscriptions = []

    def start(self):
        def start_watching():
            while not self.stopped:
                data = self.watch()
                if data:
                    for subscription in self.subscriptions:
                        subscription(data)
                else:
                    time.sleep(0.1)

        threading.Thread(target=start_watching, daemon=True).start()

    def subscribe(self, func: Callable[[Any, ], Any]):
        self.subscriptions.append(func)

    @abc.abstractmethod
    def watch(self) -> Union[None, any]:
        """
        :return: 감지된 데이터 없으면 None, 있으면 반환
        """
        pass


class CandleProvider:

    def get(self, when: datetime):
        pass



class EventProvider(DataProvider):

    def watch(self) -> Union[None, any]:
        pass
