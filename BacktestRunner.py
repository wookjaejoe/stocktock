# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import os
from datetime import date, timedelta
from datetime import datetime

from database.backtest.backtest import Backtest
from database.backtest.report import XlsxExporter
from utils import log

log.init()


def main():
    backtest = Backtest(
        begin=date(2021, 5, 17) - timedelta(days=10),
        end=date(2021, 5, 17),

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

    target_dir = backtest.dump(
        os.path.join('reports', datetime.now().strftime('%Y%m%d_%H%M%S'))
    )

    excel_exporter = XlsxExporter(
        backtest=backtest,
        target_path=os.path.join(target_dir, f'Result-{os.path.basename(target_dir)}.xlsx')
    )

    excel_exporter.export()


if __name__ == '__main__':
    main()
