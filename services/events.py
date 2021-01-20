"""
todo: 수신 - 실시간 방식으로 이벤트 수신 후 Publish
todo: 조회 - 검증(현 시각과 이벤트 시각 비교) 후 Publish
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'stocktock')))

from creon._events import EventBroker
from utils import log
import logging

logging.getLogger('schedule').setLevel(logging.ERROR)
log.init()


def main():
    event_broker = EventBroker()
    event_broker.subscribe(lambda evts: logging.info(f'Recived: {len(evts)}'))
    event_broker.start()


if __name__ == '__main__':
    main()
