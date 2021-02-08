import datetime
import logging
import os
import sys
import time

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'stocktock'))

from utils import log

log.init(logging.DEBUG)

from simulators import simulators


def main():
    market_open_time = datetime.time(hour=9, minute=0, second=0)
    while True:
        now = datetime.datetime.now()

        if now.time() > market_open_time:
            break

        print('장시작 대기...', end='\r')
        time.sleep(1)

    simulators.Simulator_2().start()
    simulators.Simulator_3().start()
    simulators.Simulator_1().start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
