from dataclasses import dataclass
from datetime import date, time


@dataclass
class Candle:
    code: str
    date: date
    time: time
    open: int
    high: int
    low: int
    close: int
    vol: int
