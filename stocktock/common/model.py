# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from dataclasses import dataclass
from datetime import date


@dataclass
class Candle:
    code: str
    date: date
    open: int
    close: int
    low: int
    high: int
    vol: int
