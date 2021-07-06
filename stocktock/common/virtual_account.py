# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from dataclasses import dataclass, field
from typing import *


@dataclass
class Holing:
    code: str
    quantity: int
    avg_price: float  # 평균 단가
    max: float = 0

    def total(self):
        return self.avg_price * self.quantity


class NotEnoughDepositException(Exception):
    pass


@dataclass
class VirtualAccount:
    deposit: int  # 예수금
    holdings: Dict[str, Holing] = field(default_factory=dict)  # 보유종목

    def has(self, code: str):
        return code in self.holdings

    def get(self, code: str):
        return self.holdings.get(code)

    def buy(self, code: str, quantity: int, price: float):
        if quantity * price > self.deposit:
            raise NotEnoughDepositException()

        if self.has(code):
            holding = self.holdings.get(code)
            total = holding.total() + quantity * price
            total_quantity = holding.quantity + quantity
            holding.avg_price = total / total_quantity
            holding.quantity += quantity
        else:
            holding = Holing(
                code=code,
                quantity=quantity,
                avg_price=price
            )

        self.deposit -= quantity * price
        self.holdings.update({code: holding})
        return holding

    def sell(self, code: str, price: float, amount_percent: float) -> int:
        holding = self.holdings.get(code)
        sell_quantity = int(holding.quantity * amount_percent)
        if sell_quantity > holding.quantity:
            sell_quantity = holding.quantity

        holding.quantity -= sell_quantity
        self.deposit += price * sell_quantity

        # 보유 수량 0개 이면, 보유 종목에서 제거
        if holding.quantity == 0:
            del self.holdings[code]

        return sell_quantity
