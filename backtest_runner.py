# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import os
from datetime import date, timedelta
from datetime import datetime

from database.backtest.report import XlsxExporter
from database.backtest.strategies.bollinger import BackTest as BlgBackTest
from utils import log

log.init()

def run(earning_line_max, stop_line, comment):
    end = date(2021, 6, 25)
    begin = end - timedelta(days=365 * 1)
    backtest = BlgBackTest(
        begin=begin,
        end=end,
        initial_deposit=1_0000_0000,
        once_buy_amount=200_0000,
        earning_line_min=5,
        earning_line=10,
        earning_line_max=earning_line_max,
        stop_line=stop_line,
        trailing_stop_rate=3,
    )
    backtest.comment = comment
    backtest.start()

    target_dir = backtest.dump(
        os.path.join('reports', datetime.now().strftime('%Y%m%d_%H%M%S'))
    )

    XlsxExporter(
        backtest=backtest,
        target_path=os.path.join(target_dir, f'Result-{os.path.basename(target_dir)}.xlsx')
    ).export()

def main():
    run(earning_line_max=15, stop_line=-10, comment='')
    # for earning_line in [12, 15, 18]:
    #     for stop_line in [-8, -10, -12]:


if __name__ == '__main__':
    main()
