import abc
import logging
import threading
from datetime import date, timedelta, datetime
from typing import *

import creon.charts
import creon.stocks
import database as db


class EventPublisher(abc.ABC):

    def start_async(self):
        threading.Thread(target=self._start).start()

    def start(self):
        self._start()

    @abc.abstractmethod
    def _start(self):
        pass


class MinuteCandleProvdider(EventPublisher):

    def __init__(self, code: str, begin: date, end: date):
        assert len(code) == 6, f'Malformed code: {code}'
        if not db.Stock.exists(code=code):
            db.Stock(code=code, name=creon.stocks.get_name(code)).insert(commit=True)

        self.code = code
        self.stock_id = db.Stock.find_by_code(code).id
        self.begin = begin
        self.end = end
        self.subscribers: List[Callable[[creon.charts.ChartData], None]] = []
        self.stopped = False

    def _start(self):
        def run_for(date_at: date):
            exists = db.MinuteCandle.exists(
                date=date_at
            )

            if not exists:
                # 해당 일자 캔들이 존재하지 않으면, 크레온에서 받아와 넣는다
                chart = creon.charts.request_by_term(
                    code=creon.stocks.find(code=self.code).code,
                    chart_type=creon.charts.ChartType.MINUTES,
                    begin=date_at,
                    end=date_at + timedelta(days=10)
                )

                logging.debug(f'Inserting {len(chart)} candles for {self.code}')
                db.MinuteCandle.insert_many(
                    [
                        db.MinuteCandle(
                            stock_id=self.stock_id,
                            date=candle.datetime.date(),
                            time=candle.datetime.time(),
                            open=candle.open,
                            close=candle.close,
                            low=candle.low,
                            high=candle.high
                        ) for candle in chart
                    ]
                )

            candles = db.MinuteCandle.query().filter_by(
                stock_id=self.stock_id,
                date=date_at
            ).all()

            if candles:
                candles.sort(key=lambda candle: datetime.combine(candle.date, candle.time))
                for subscriber in self.subscribers:
                    for candle in candles:
                        subscriber(candle)

        cur_date = self.begin
        while not self.stopped and self.end >= cur_date:
            run_for(cur_date)
            cur_date += timedelta(days=1)

    def stop(self):
        self.stopped = True
