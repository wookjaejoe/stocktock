import logging
import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'stocktock'))

from utils import log

log.init(logging.DEBUG)
import time

from simulators import simulators


def main():
    simulators.Simulator_2().start()
    simulators.Simulator_3().start()
    simulators.Simulator_1().start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
