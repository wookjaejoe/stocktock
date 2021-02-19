import abc
import threading
from datetime import date, timedelta
from typing import *

from creon import charts


class EventPublisher(abc.ABC):

    def start_async(self):
        threading.Thread(target=self._start).start()

    def start(self):
        self._start()

    @abc.abstractmethod
    def _start(self):
        pass


class PastMinuteCandleProvdider(EventPublisher):

    def __init__(self, code: str, begin: date, end: date):
        self.code = code
        self.begin = begin
        self.end = end
        self.subscribers: List[Callable[[charts.ChartData], None]] = []
        self.stopped = False

    def _start(self):
        begin = self.begin

        while not self.stopped:
            end = begin + timedelta(days=10)
            if end > self.end:
                end = self.end
                self.stopped = True

            chart = charts.request_by_term(code=self.code, chart_type=charts.ChartType.MINUTES, begin=begin, end=end)
            for candle in chart:
                self._publish(candle)

            begin = end + timedelta(days=1)

    def stop(self):
        self.stopped = True

    def _publish(self, candle: charts.ChartData):
        for subscriber in self.subscribers:
            subscriber(candle)


class CreonBuiltinEventPublisher(EventPublisher):
    def _start(self):
        pass

    def _publish(self, data):
        pass

# class BreakAbove5MaEventpublisher(EventPublisher):
#     def __init__(self, price_provider):
