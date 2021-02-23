import datetime
import logging
import os
import sys
import time
from typing import *

from creon import stocks, mas

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'stocktock'))

from utils import log

log.init(logging.DEBUG)

from simulation import simulators


def main():
    available_codes = stocks.get_availables()
    available_codes = [code for code in available_codes if mas.get_calculator(code).is_straight()]
    details: Dict[str, stocks.StockDetail2] = {detail.code: detail for detail in stocks.get_details(available_codes)}
    available_codes = [code for code in available_codes if
                       2000_0000_0000 < details.get(code).capitalization() if
                       available_codes.index(code)]

    market_open_time = datetime.time(hour=9, minute=0, second=0)
    logging.info('APP STARTED')
    logging.info(f'장시작 확인 및 대기 - 장시작: {market_open_time}')
    while True:
        now = datetime.datetime.now()

        if now.time() > market_open_time:
            break

        time.sleep(1)

    logging.info('LET START SIMULATIONS')
    simulators.Simulator_2(available_codes).start()
    simulators.Simulator_1(available_codes).start()
    # simulators.Simulator_1().start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
