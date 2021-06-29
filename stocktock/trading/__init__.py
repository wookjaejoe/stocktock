import abc
import csv
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import *

from dateutil.parser import parse as parse_datetime

from creon import stocks, metrics, traders
from utils import calc
from utils.slack import WarrenSession, Message
from utils.strings import strip_multiline_string


@dataclass
class Holding:
    created: datetime
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
                line = [s.strip() for s in line]
                created = parse_datetime(line[0])
                code = line[1]
                count = int(line[2])
                price = int(line[3])
                self.holdings.append(Holding(created, code, count, price))

    def save(self):
        with open(self.path, 'w', encoding='utf-8', newline='') as f:
            csv_writer = csv.writer(f)
            for holding in self.holdings:
                csv_writer.writerow([holding.created, holding.code, holding.count, holding.price])

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
class OrderRecord:
    what: str
    order_type: str
    code: str
    name: str
    order_price: int
    order_count: int
    total: int
    earning_rate: float = None
    earning_price: int = None
    memo: str = None

    def summit(self, logger, warren_session: WarrenSession):
        if self.order_type == 'BUY':
            emoji = ':moneybag:'
        else:
            try:
                int(self.earning_rate)  # check number
                if self.earning_rate > 0:
                    emoji = ':smiley:'
                else:
                    emoji = ':rage:'
            except:
                emoji = ''

        msg = f'''
        {emoji} {self.what}
        {self.order_type} {self.name}({self.code}) for ₩{self.order_price} × {self.order_count}: ₩{self.total}
        '''

        if self.earning_price and self.earning_rate:
            msg += f'''
            {'+' if self.earning_price >= 0 else ''}{self.earning_price}({'+' if round(self.earning_rate, 2) >= 0 else ''}{round(self.earning_rate, 2)}%)
            '''

        if self.memo:
            msg += f'''
            ```
            {self.memo}
            ```
            '''

        msg = strip_multiline_string(msg)
        warren_session.send(Message(msg))
        logger.critical(msg)


class Bot(abc.ABC):
    def __init__(self, name, codes):
        self.name = name
        self.codes = codes
        self.wallet = Wallet(name)
        self.logger = logging.getLogger(name)
        self.warren_session: Optional[WarrenSession] = None
        self.bend_line = 5
        self.stop_line = -3
        self.max_holding_count = 7000

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

                time.sleep(5)

                try:
                    self.check_stop_line()
                except:
                    self.logger.error('An error occured while checking stop line.', exc_info=sys.exc_info())

                time.sleep(5)

        threading.Thread(target=work, daemon=True).start()

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

            if not detail.price:
                logging.warning('The price is 0: ' + holding.code)
                continue

            cur_price = detail.price
            earnings_rate = calc.earnings_ratio(holding.price, cur_price)

            try:
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
            except:
                logging.exception(f'Failed to sell {detail.code}')

    def try_buy(self, code: str, what: str, order_price: int = None, memo: str = None):
        if self.wallet.has(code):
            return

        if len(self.wallet.holdings) >= self.max_holding_count:
            logging.warning('The number of holdings has reached the maximum holdings.')
            return

        if not order_price:
            detail = list(stocks.get_details([code]))[0]
            order_price = detail.price

        order_count = int(100_0000 / order_price)
        order_total = order_price * order_count

        try:
            traders.buy(code=code, price=order_price, count=order_count)
            self.wallet.put(Holding(created=datetime.now(), code=code, count=order_count, price=order_price))
            OrderRecord(
                what=what,
                order_type='BUY',
                code=code,
                name=stocks.get_name(code),
                order_price=order_price,
                order_count=order_count,
                total=order_total,
                memo=memo
            ).summit(logger=self.logger, warren_session=self.warren_session)
        except:
            logging.exception('Failed to try to buy ' + code)

    def try_sell(self, code: str, what: str, order_price: int = None):
        return  # fixme
        if not self.wallet.has(code):
            return

        holding = self.wallet.get(code)

        if not order_price:
            detail = list(stocks.get_details([code]))[0]
            order_price = detail.price

        order_total = order_price * holding.quantity
        holding_total = holding.price * holding.quantity

        try:
            traders.sell(code=code, price=order_price, count=holding.quantity)
            self.wallet.delete(code)
            OrderRecord(
                what=what,
                order_type='SELL',
                code=code,
                name=stocks.get_name(code),
                order_price=order_price,
                order_count=holding.quantity,
                total=order_total,
                earning_price=order_total - holding_total,
                earning_rate=calc.earnings_ratio(holding.price, order_price)
            ).summit(logger=self.logger, warren_session=self.warren_session)
        except:
            logging.exception('Failed to try to sell ' + code)


class Simulator_2(Bot):
    """
    2번
    """

    def __init__(self, codes):
        super().__init__('5MA_상향돌파', codes)

    def run(self):
        whitelist = []
        for code in self.codes:
            try:
                ma_calc = metrics.get_calculator(code)
                ma_5_yst = ma_calc.get(5, pos=-1)
                ma_20_yst = ma_calc.get(20, pos=-1)
                ma_20_yst_2 = ma_calc.get(20, pos=-2)
                ma_60_yst = ma_calc.get(60, pos=-1)
                ma_120_yst = ma_calc.get(120, pos=-1)

                if ma_20_yst > ma_5_yst > ma_60_yst > ma_120_yst \
                        and ma_20_yst > ma_20_yst_2 \
                        and len([candle for candle in ma_calc.chart[-5:] if candle.open < candle.close]) > 0:
                    whitelist.append(code)
            except:
                continue

        details = stocks.get_details(whitelist)

        # 모든 취급 종목에 대해...
        for detail in details:
            try:
                # 전일 기준 5MA, 20MA 구한다
                ma_calc = metrics.get_calculator(detail.code)
                ma_5_yst = ma_calc.get(5, pos=-1)
                if detail.open < ma_5_yst <= detail.price < ma_5_yst * 1.025:
                    self.try_buy(
                        code=detail.code,
                        what='5MA 상향돌파',
                        order_price=detail.price,
                        # memo=f'''
                        #     ma_20_yst > ma_5_yst > ma_60_yst > ma_120_yst
                        #     and ma_20_yst > ma_20_yst_2
                        #     and len([candle for candle in ma_calc.chart[-5:] if candle.open < candle.close]) > 0
                        #     and open < ma_5_yst <= cur_price < ma_5_yst * 1.025
                        #     '''
                    )
            except:
                logging.exception(f'Failed to simulate for {detail.code} in {self.name}')
