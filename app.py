import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'services'))
sys.path.append(os.path.join(basedir, 'stocktock'))
import csv
import time
import threading

from creon import events, traders, stocks
from utils import log
import logging
import argparse
from dataclasses import dataclass
from typing import *
import schedule

log.init()

creon_trader = traders.Trader()

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--sell_only', action='store_true')
args = arg_parser.parse_args()
sell_only = args.sell_only

logging.getLogger('schedule').setLevel(logging.WARNING)


@dataclass
class Holding:
    code: str
    count: int
    price: int


class Wallet:
    CSV_PATH = 'wallet.csv'

    def __init__(self):
        self.holdings: List[Holding] = []
        self.load()

    def load(self):
        if not os.path.exists(self.CSV_PATH):
            return

        self.holdings = []

        with open(self.CSV_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for line in csv_reader:
                code = line[0]
                count = int(line[1])
                price = int(line[2])
                self.holdings.append(Holding(code, count, price))

    def save(self):
        with open(self.CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            csv_writer = csv.writer(f)
            for holding in self.holdings:
                csv_writer.writerow([holding.code, holding.count, holding.price])

    def has(self, code):
        return code in [holding.code for holding in self.holdings]

    def get(self, code):
        for holding in self.holdings:
            if code == holding.code:
                return holding

    def put(self, holding: Holding):
        self.holdings.append(holding)
        self.save()

    def delete(self, code):
        self.holdings.remove(self.get(code))
        self.save()


# 주문 로그 - 시각, 매수/매도, 종목코드, 종목명, 살때/팔때 가격, 산/판 개수 (팔면)수익률(수익금), 이벤트ID
# 잔고 관리 - 보유 종목, 보유 개수, 매수가
wallet = Wallet()


def callback(event: events.Event):
    if event.cancel:
        return

    if event.category in [45, 46]:
        order = on_45_46(event)
    elif event.category in [44, 47]:
        order = on_44_47(event)
    else:
        return

    if order:
        record = [
            event.category,
            # 주문 타입, 주문 종목, 주문 종목명, 주문가, 주문 개수
            order.order_type.name, order.code, stocks.get_name(order.code), order.order_price, order.order_count,
            order.total_price
        ]

        if order.order_type == traders.OrderType.SELL:
            holding = wallet.get(event.code)
            return_price = order.total_price - holding.price * holding.count
            return_rate = (order.total_price / holding.price * holding.count) - 1 * 100
            record.append(return_rate)
            record.append(return_price)
            wallet.delete(order.code)
        elif order.order_type == traders.OrderType.BUY:
            wallet.put(Holding(code=order.code, count=order.order_count, price=order.order_price))

        logging.critical(', '.join([str(v) for v in record]))


def on_45_46(event: events.Event) -> traders.VirtualOrder:
    if not event.cancel and not wallet.has(event.code):
        return traders.VirtualOrder(code=event.code,
                                    order_type=traders.OrderType.BUY,
                                    limit=100_0000)


def on_44_47(event: events.Event) -> traders.VirtualOrder:
    if not event.cancel and wallet.has(event.code):
        return traders.VirtualOrder(code=event.code,
                                    order_type=traders.OrderType.SELL,
                                    count=wallet.get(event.code).count)


def on_watch_10sec():
    for holding in wallet.holdings:
        try:
            cur_price = stocks.get_detail(holding.code).cprice
        except:
            logging.warning(f'Failed to get expected price for {holding.code}')
            continue

        return_rate = (cur_price / holding.price - 1) * 100
        if return_rate < -3:
            wallet.delete(holding.code)

        time.sleep(0.05)


def watch_10sec():
    schedule.every(15).seconds.do(on_watch_10sec)

    def do_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=do_schedule).start()


def main():
    watch_10sec()
    events.subscribe(callback)
    events.start()


if __name__ == '__main__':
    main()
