import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'services'))
sys.path.append(os.path.join(basedir, 'stocktock'))
import csv
import time
import threading
from utils import calc
from creon import events, traders, stocks
from utils import log
import logging
import argparse
from dataclasses import dataclass
from typing import *
import schedule
import traceback

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


@dataclass(init=False)
class Record:
    what: str
    order_type: str
    code: str
    name: str
    order_price: int
    order_count: int
    total: int
    earning_rate: float = 0
    earning_price: int = 0
    capital: int = 0

    def __init__(self, what, order_type: traders.OrderType, code, order_price, order_count):
        self.what = what
        self.order_type = order_type.name
        self.code = code
        self.name = stocks.get_name(code)
        self.order_price = order_price
        self.order_count = order_count
        self.total = order_price * order_count
        self.capital = stocks.get_capital(code)

        if order_type == traders.OrderType.SELL:
            holding = wallet.get(code)
            self.earning_rate = calc.earnings_ratio(buy_price=holding.price, sell_price=order_price)
            self.earning_price = self.total - holding.price * holding.count
            wallet.delete(code)
        elif order_type == traders.OrderType.BUY:
            wallet.put(Holding(code=code, count=order_count, price=order_price))

    def summit(self):
        logging.critical(', '.join([str(v) for v in list(self.__dict__.values())]))


not_handling_words = [
    'TIGER',
    'KOSEF',
    'KODEX',
    'ARIRANG',
    'HANARO',
    'KBSTAR',
    'KINDEX',
    'TREX'
]


def callback(event: events.Event):
    if event.cancel:
        # 이벤트 취소 대응 안함
        return

    if not stocks.is_kos(event.code):
        # KOSPI, KOSDAQ 아니면 취급 안함
        return

    if stocks.get_supervision(event.code) == 1:
        # 관리 종목 취급 안함
        return

    if stocks.get_status(event.code) != 0:
        # 정상 아닌 종목 취급 안함
        return

    stock_name = stocks.get_name(event.code)
    for not_handling_word in not_handling_words:
        if not_handling_word in stock_name:
            return

    if event.category in [45, 46]:
        order = on_45_46(event)
    elif event.category in [44, 47]:
        order = on_44_47(event)
    else:
        return

    if order:
        Record(
            what=event.category,
            order_type=order.order_type,
            code=event.code,
            order_price=order.order_price,
            order_count=order.order_count
        ).summit()


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


STOP_LINE = -5


def check_stop_line():
    details: Dict[str, stocks.StockDetail2] = {
        detail.code: detail for detail in
        stocks.get_details([holding.code for holding in wallet.holdings])
    }

    for holding in wallet.holdings:
        try:
            cur_price = details.get(holding.code).price
            earnings_rate = calc.earnings_ratio(holding.price, cur_price)

            if earnings_rate < STOP_LINE:
                Record(
                    what=f'손절라인 {STOP_LINE}%',
                    order_type=traders.OrderType.SELL,
                    code=holding.code,
                    order_price=cur_price,
                    order_count=holding.count
                ).summit()
        except:
            logging.debug(traceback.format_exc())
            logging.warning(f'Failed to get expected price for {holding.code}')


def start_scheduling():
    # 손절라인 체크
    schedule.every(15).seconds.do(check_stop_line)

    def do_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=do_schedule, daemon=True).start()


def check_jumping():
    # 장전매수/시가매매 - https://hwiiiii.tistory.com/entry/%EC%A3%BC%EC%8B%9D-%EC%A2%85%EA%B0%80-%EC%8B%9C%EA%B0%80%EB%9E%80-%EA%B0%AD-%EB%A7%A4%EB%A7%A4%EC%97%90-%EB%8C%80%ED%95%B4

    def run():
        details = stocks.get_details([stock.code for stock in stocks.ALL_STOCKS if stocks.get_status(stock.code) == 0])
        for detail in details:
            if detail.yesterday_close * 1.05 <= detail.open:
                Record(
                    what=f'갭상승 2%',
                    order_type=traders.OrderType.BUY,
                    code=detail.code,
                    order_price=detail.price,
                    order_count=int(100_0000 / detail.price)
                ).summit()

    # threading.Thread(target=run, daemon=True).start()
    run()


def main():
    # check_jumping()
    start_scheduling()
    events.subscribe(callback)
    events.start()


if __name__ == '__main__':
    main()
