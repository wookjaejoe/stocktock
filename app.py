import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'services'))
sys.path.append(os.path.join(basedir, 'stocktock'))

from creon import events, traders
from utils import log
import logging

log.init()

trader = traders.Trader()


# Rule 관리
def callback(event: events.Event):
    """
    - 45|46->44|47
    - todo: 58->47|59
    """
    category = event.category
    code = event.code

    if category == 45 or category == 46:
        if event.cancel:
            logging.warning(f'EVENT CANCELED - {event}')
            return
        else:
            order = traders.Order(
                order_type=traders.OrderType.BUY,
                code=code,
                count=1
            )
    elif category == 44 or category == 47:
        if event.cancel:
            logging.warning(f'EVENT CANCELED - {event}')
            return
        else:
            order = traders.Order(
                order_type=traders.OrderType.SELL,
                code=code,
                count=1
            )
    else:
        return

    if order:
        logging.info(f'{event}')
        trader.request_order(order)


def main():
    events.subscribe(callback)
    events.start()


if __name__ == '__main__':
    main()
