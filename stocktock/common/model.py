# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from dataclasses import dataclass
from datetime import date
from typing import *

T = TypeVar('T')


@dataclass
class Candle:
    code: str
    date: date
    open: int
    close: int
    low: int
    high: int
    vol: int


@dataclass(init=False)
class CandlesGroupByCode(Generic[T]):
    def __init__(self, candles: List[T]):
        self._candles_by_code: Dict[str, List[T]] = {}
        for candle in candles:
            code = candle.code
            if code not in self._candles_by_code:
                self._candles_by_code.update({code: []})

            self._candles_by_code.get(code).append(candle)

    def get(self, code: str) -> List[T]:
        return self._candles_by_code.get(code)

    def codes(self):
        return self._candles_by_code.keys()