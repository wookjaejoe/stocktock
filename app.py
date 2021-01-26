import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'services'))
sys.path.append(os.path.join(basedir, 'stocktock'))

from creon import events, traders
from utils import log
import logging
import argparse
# from kiwoom.traders import Trader as KiwoomTrader

log.init()

creon_trader = traders.Trader()

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--sell_only', action='store_true')
args = arg_parser.parse_args()
sell_only = args.sell_only


# Rule 관리
def callback(event: events.Event):
    """
    - 45|46->44|47
    - todo: 58->47|59
    """
    category = event.category
    code = event.code

    if category == 45 or category == 46:
        if sell_only:
            return

        if event.cancel:  # 매수 시그널이 취소되면, 하나 판다
            order = traders.Order(
                order_type=traders.OrderType.SELL,
                code=code,
                count=1
            )
        else:  # 매수 시그널 발생 시, 하나 매수
            order = traders.Order(
                order_type=traders.OrderType.BUY,
                code=code,
                count=1
            )
    elif category == 44 or category == 47:
        if event.cancel:  # 매도 시그널 취소 시 아무것도 안함
            return
        else:  # 매도 시그널 발생 시 매도
            order = traders.Order(
                order_type=traders.OrderType.SELL,
                code=code,
                count=1
            )
    else:
        return

    if order:
        logging.info(f'{event}')
        order.magic_value = event
        creon_trader.request_order(order)

        # try:
        #     if order.order_type == traders.OrderType.BUY:
        #         KiwoomTrader.buy(code=order.code[1:], count=1)
        #     elif order.order_type == traders.OrderType.SELL:
        #         KiwoomTrader.sell(code=order.code[1:], count=1)
        # except BaseException as e:
        #     logging.warning(f'Kiwoom Trade Failure: {e}')


def main():
    events.subscribe(callback)
    events.start()


if __name__ == '__main__':
    main()
