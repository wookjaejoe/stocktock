import datetime
import logging
import os
import sys
import time

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'stocktock'))

from utils import log

log.init(logging.DEBUG)

from simulation import simulators


def main():
    market_open_time = datetime.time(hour=9, minute=0, second=0)
    logging.info('APP STARTED')
    logging.info(f'장시작 확인 및 대기 - 장시작: {market_open_time}')
    while True:
        now = datetime.datetime.now()

        if now.time() > market_open_time:
            break

        time.sleep(1)

    logging.info('LET START SIMULATIONS')
    simulators.Simulator_2().start()
    # simulators.Simulator_3().start()
    # simulators.Simulator_1().start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
