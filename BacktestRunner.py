# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from datetime import date

from database.backtest import Backtest
from utils import log

log.init()


def main():
    backtest = Backtest(
        begin=date(2020, 1, 1),
        end=date(2021, 6, 30),  # 코로나 하락장

        limit_holding_count=100,
        limit_buy_amount=100_0000,
        limit_holding_days=20,

        earn_line=7,
        stop_line=-5,
        initial_deposit=1_0000_0000,
        tax_percent=0.25,
        fee_percent=0.015
    )
    backtest.start()


if __name__ == '__main__':
    main()
