import abc
import threading
from datetime import date, timedelta
from typing import *

from creon import charts
from model import Candle


class EventPublisher(abc.ABC):

    def start_async(self):
        threading.Thread(target=self._start).start()

    def start(self):
        self._start()

    @abc.abstractmethod
    def _start(self):
        pass


class MinuteCandleProvdider(EventPublisher):

    def __init__(self, code: str, begin: date, end: date, period=1):
        self.code = code
        self.begin = begin
        self.end = end
        self.period = period
        self.subscribers: List[Callable[[Candle], None]] = []
        self.stopped = False

    def _start(self):
        begin = self.begin

        while not self.stopped:
            end = begin + timedelta(days=10 * self.period)
            if end > self.end:
                end = self.end
                self.stopped = True

            chart = charts.request_by_term(
                code=self.code,
                chart_type=charts.ChartType.MINUTE,
                begin=begin,
                end=end,
                period=self.period)
            for candle in chart:
                if candle.date > self.end:
                    break

                self._publish(candle)

            begin = end + timedelta(days=1)

    def stop(self):
        self.stopped = True

    def _publish(self, candle: Candle):
        for subscriber in self.subscribers:
            subscriber(candle)


class CreonBuiltinEventPublisher(EventPublisher):
    def _start(self):
        pass

    def _publish(self, data):
        pass

# class BreakAbove5MaEventpublisher(EventPublisher):
#     def __init__(self, price_provider):
