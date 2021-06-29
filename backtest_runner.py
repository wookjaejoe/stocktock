# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import os
from datetime import date, timedelta
from datetime import datetime

from database.backtest.strategies.bollinger import BackTest as BlgBackTest
from database.backtest.report import XlsxExporter
from utils import log
from kospi_200 import kospi_200_codes

log.init()


def main():
    end = date(2021, 5, 17)
    days = 30
    backtest = BlgBackTest(
        available_codes=kospi_200_codes(),
        begin=end - timedelta(days=days),
        end=end,
        initial_deposit=1_0000_0000,
        once_buy_amount=1000_0000,
        earning_line_min=5,
        earning_line=10,
        earning_line_max=15,
        stop_line=-10,
        trailing_stop_rate=3
    )

    backtest.start()

    target_dir = backtest.dump(
        os.path.join('reports', datetime.now().strftime('%Y%m%d_%H%M%S'))
    )

    XlsxExporter(
        backtest=backtest,
        target_path=os.path.join(target_dir, f'Result-{os.path.basename(target_dir)}.xlsx')
    ).export()


if __name__ == '__main__':
    main()
