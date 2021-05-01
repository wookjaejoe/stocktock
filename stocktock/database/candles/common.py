from dataclasses import dataclass
from datetime import date


@dataclass
class Candle:
    date: date
    open: int
    close: int
    low: int
    high: int
    vol: int
