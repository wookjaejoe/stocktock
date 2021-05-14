# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

from datetime import date, timedelta

from database.backtest3 import Backtest


def main():
    backtest = Backtest(
        begin=date.today() - timedelta(days=100),
        end=date.today(),
        limit_holding_count=100,
        limit_buy_amount=100_0000,
        earn_line=7,
        stop_line=-5
    )
    backtest.start()
    print()


if __name__ == '__main__':
    main()
