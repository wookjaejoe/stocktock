# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from datetime import date, timedelta

from database.backtest import Backtest
from utils import log

log.init()


def main():
    backtest = Backtest(
        # begin=date(2021, 1, 1),
        begin=date.today() - timedelta(days=365),
        end=date.today(),

        limit_holding_count=100,
        limit_buy_amount=100_0000,
        limit_keeping_days=20,

        earn_line=7,
        stop_line=-5,
        initial_deposit=1_0000_0000,
        tax_percent=0.25,
        fee_percent=0.015
    )
    backtest.start()
    backtest.save_report()


if __name__ == '__main__':
    main()
