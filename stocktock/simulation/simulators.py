import abc
import csv
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import *

from creon import stocks, mas, traders
from utils import calc
from utils.slack import WarrenSession, Message

# 취급 코드들


@dataclass
class Holding:
    code: str
    count: int
    price: int


class Wallet:

    def __init__(self, name):
        folder = 'wallets'
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, f'{name}.csv')
        self.holdings: List[Holding] = []

        try:
            self.load()
        except:
            self.save()

    def load(self):
        self.holdings = []

        with open(self.path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for line in csv_reader:
                code = line[0]
                count = int(line[1])
                price = int(line[2])
                self.holdings.append(Holding(code, count, price))

    def save(self):
        with open(self.path, 'w', encoding='utf-8', newline='') as f:
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


@dataclass
class Record:
    what: str
    order_type: str
    code: str
    name: str
    order_price: int
    order_count: int
    total: int
    earning_rate: float = None
    earning_price: int = None

    def summit(self, logger, warren_session: WarrenSession):
        msg = ':dollar: ' + ', '.join(['N/A' if v is None else str(v) for v in list(self.__dict__.values())])
        warren_session.send(Message(msg))
        logger.critical(msg)


class Simulator(abc.ABC):
    def __init__(self, name, codes):
        self.name = name
        self.codes = codes
        self.wallet = Wallet(name)
        self.logger = logging.getLogger(name)
        self.warren_session: Optional[WarrenSession] = None
        self.bend_line = 7
        self.stop_line = -5

    @abc.abstractmethod
    def run(self):
        ...

    def start(self):
        self.warren_session = WarrenSession(self.name)

        def work():
            while True:
                self.logger.debug('# HEALTH CHECK #')
                try:
                    self.run()
                except:
                    self.logger.error('An error occured while running the simulation.', exc_info=sys.exc_info())

                time.sleep(7)

                try:
                    self.check_stop_line()
                except:
                    self.logger.error('An error occured while checking stop line.', exc_info=sys.exc_info())

                time.sleep(7)

        threading.Thread(target=work).start()

    def check_stop_line(self):
        details: Dict[str, stocks.StockDetail2] = {
            detail.code: detail for detail in
            stocks.get_details([holding.code for holding in self.wallet.holdings])
        }

        for holding in self.wallet.holdings:
            detail = details.get(holding.code)

            if not detail:
                logging.warning('The detail is null: ' + holding.code)
                continue

            cur_price = detail.price
            earnings_rate = calc.earnings_ratio(holding.price, cur_price)
            if earnings_rate < self.stop_line:
                # 손절
                self.try_sell(code=holding.code,
                              what=f'손절 {self.stop_line}%',
                              order_price=detail.price)
            elif earnings_rate > self.bend_line:
                # 익절
                self.try_sell(code=holding.code,
                              what=f'익절 {self.bend_line}%',
                              order_price=detail.price)

    def try_buy(self, code: str, what: str, order_price: int = None):
        if self.wallet.has(code):
            return

        if not order_price:
            detail = list(stocks.get_details([code]))[0]
            order_price = detail.price

        order_count = int(100_0000 / order_price)
        order_total = order_price * order_count
        self.wallet.put(holding=Holding(code=code, count=order_count, price=order_price))
        Record(
            what=what,
            order_type='BUY',
            code=code,
            name=stocks.get_name(code),
            order_price=order_price,
            order_count=order_count,
            total=order_total
        ).summit(logger=self.logger, warren_session=self.warren_session)
        traders.buy(code=code, price=order_price, count=order_count)

    def try_sell(self, code: str, what: str, order_price: int = None):
        if not self.wallet.has(code):
            return

        holding = self.wallet.get(code)

        if not order_price:
            detail = list(stocks.get_details([code]))[0]
            order_price = detail.price

        order_total = order_price * holding.count
        holding_total = holding.price * holding.count
        self.wallet.delete(code)
        Record(
            what=what,
            order_type='SELL',
            code=code,
            name=stocks.get_name(code),
            order_price=order_price,
            order_count=holding.count,
            total=order_total,
            earning_price=order_total - holding_total,
            earning_rate=calc.earnings_ratio(holding.price, order_price)
        ).summit(logger=self.logger, warren_session=self.warren_session)
        traders.sell(code=code, price=order_price, count=holding.count)


class Simulator_2(Simulator):
    """
    2번
    """

    def __init__(self, codes):
        super().__init__('[2]5일선_상향돌파', codes)

    def run(self):
        details = stocks.get_details(self.codes)
        # 모든 취급 종목에 대해...
        for detail in details:
            try:
                # 전일 기준 5MA, 20MA 구한다
                ma_calc = mas.get_calculator(detail.code)
                ma_5 = ma_calc.get(mas.MA.MA_5, pos=-1)
                ma_20 = ma_calc.get(mas.MA.MA_20, pos=-1)

                if ma_20 < detail.open < ma_5 <= detail.price < ma_5 * 1.02:
                    self.try_buy(
                        code=detail.code,
                        what='[2]5일선_상향돌파',
                        order_price=detail.price
                    )
            except:
                logging.exception(f'Failed to simulate for {detail.code} in {self.name}')


class Simulator_1(Simulator):
    """
    2번
    """

    def __init__(self, codes):
        super().__init__('골든데드크로스', codes)
        self.bend_line = 12
        self.stop_line = -5

    def run(self):
        for detail in stocks.get_details([holding.code for holding in self.wallet.holdings]):
            ma_calc = mas.get_calculator(detail.code)
            ma_5_cur = ma_calc.get(mas.MA.MA_5, cur_price=detail.price)
            ma_5_yst = ma_calc.get(mas.MA.MA_5, pos=-1)
            ma_10_yst = ma_calc.get(mas.MA.MA_10, pos=-1)
            if ma_5_yst > ma_10_yst > ma_5_cur:
                self.try_sell(code=detail.code, what='데드크로스', order_price=detail.price)

        # 모든 취급 종목에 대해...
        for detail in stocks.get_details(self.codes):
            try:
                # 전일 기준 5MA, 20MA 구한다
                ma_calc = mas.get_calculator(detail.code)
                ma_5_cur = ma_calc.get(mas.MA.MA_5, cur_price=detail.price)
                ma_5_yst = ma_calc.get(mas.MA.MA_5, pos=-1)
                ma_10_cur = ma_calc.get(mas.MA.MA_10, cur_price=detail.price)
                ma_10_yst = ma_calc.get(mas.MA.MA_10, pos=-1)

                if ma_5_yst < ma_10_yst < ma_5_cur < ma_10_cur * 1.03:
                    self.try_buy(code=detail.code, what='골든크로스', order_price=detail.price)
            except:
                logging.exception(f'Failed to simulate for {detail.code} in {self.name}')


####
# DEPRECATED !!!
####
class Simulator_3(Simulator):
    """
    1번
    """

    def __init__(self, codes):
        super().__init__('[1]MA60_120_하방터치', codes)

    def run(self):
        # 취급 종목의 상세정보 구한다
        details = stocks.get_details(self.codes)
        for detail in details:
            try:
                # 본 종목의 60/120MA를 구한다
                ma_calc = mas.get_calculator(detail.code)
                ma_60 = ma_calc.get(mas.MA.MA_60, cur_price=-1)
                ma_120 = ma_calc.get(mas.MA.MA_120, cur_price=-1)

                if ma_60 <= detail.price <= ma_60 * 1.02:
                    self.try_buy(
                        code=detail.code,
                        what='[1]60MA_하방터치',
                        order_price=detail.price
                    )
                elif ma_120 <= detail.price <= ma_120 * 1.02:
                    self.try_buy(
                        code=detail.code,
                        what='[1]120MA_하방터치',
                        order_price=detail.price
                    )
            except:
                logging.exception(f'Failed to simulate for {detail.code} in {self.name}')

        time.sleep(10)
