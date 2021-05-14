from dataclasses import dataclass
from datetime import date
from typing import *
from multiprocessing.pool import ThreadPool

@dataclass
class Candle:
    date: date
    open: int
    close: int
    low: int
    high: int
    vol: int
