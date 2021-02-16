import time
from dataclasses import dataclass
from typing import *

from simulation import simulators
from creon import stocks
from utils import calc


wallet = simulators.Simulator_2().wallet

@dataclass(init=False)
class HoldingStockEvaluation:
    code: str
    name: str
    buy_price: int
    cur_price: int
    count: int
    buy_total: int
    cur_total: int
    earnings: int
    earnings_rate: float

    def __init__(self, holding: simulators.Holding, detail: stocks.StockDetail2):
        self.code = holding.code  # 종목코드
        self.name = detail.name  # 종목명
        self.buy_price = holding.price  # 매수가
        self.cur_price = detail.price  # 현재가(종가)
        self.count = holding.count
        self.buy_total = holding.price * holding.count  # 매수가 * 개수
        self.cur_total = detail.price * holding.count  # 현재가 * 개수
        self.earnings = detail.price * holding.count - holding.price * holding.count  # 수익금
        self.earnings_rate = calc.earnings_ratio(holding.price, detail.price)  # 수익률


@dataclass(init=False)
class Statistics:
    evaluations: List[HoldingStockEvaluation]

    def __init__(self):
        self.evaluations = []
        details = {detail.code: detail for detail in stocks.get_details([holding.code for holding in wallet.holdings])}
        for holding in wallet.holdings:
            ev = HoldingStockEvaluation(holding, details.get(holding.code))
            self.evaluations.append(ev)
            time.sleep(0.1)


def main():
    statistics = Statistics()
    print('=' * 80)
    for ev in statistics.evaluations:
        values = list(ev.__dict__.values())
        print(','.join([str(v) for v in values]))

    print('=' * 80)

    earnings = [ev.earnings for ev in statistics.evaluations]
    earnings_rates = [ev.earnings_rate for ev in statistics.evaluations]
    print(f'max(earnings), {max(earnings)}')
    print(f'max(earnings_rates), {max(earnings_rates)}')
    print(f'min(earnings), {min(earnings)}')
    print(f'min(earnings_rates), {min(earnings_rates)}')
    print(f'sum(earnings), {sum(earnings)}')
    print(f'sum(earnings_rates), {sum(earnings_rates)}')
    print(f'avg(earnings), {sum(earnings) / len(statistics.evaluations)}')
    print(f'avg(earnings_rates), {sum(earnings_rates) / len(statistics.evaluations)}')


if __name__ == '__main__':
    main()
