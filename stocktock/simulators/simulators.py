import csv
import logging
import threading
import time
import traceback
from dataclasses import dataclass
from typing import *

from creon import events, stocks, mas
from utils import calc
from utils.slack import WarrenSession, Message


@dataclass
class Holding:
    code: str
    count: int
    price: int


class Wallet:

    def __init__(self, name):
        self.path = f'{name}.csv'
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
    earning_rate: float = 0
    earning_price: int = 0

    def summit(self, logger, warren_session: WarrenSession):
        msg = ', '.join([str(v) for v in list(self.__dict__.values())])
        warren_session.send(Message(msg))
        logger.critical(msg)


class Simulator:
    def __init__(self, name, stop_line=7):
        self.name = name
        self.wallet = Wallet(name)
        self.logger = logging.getLogger(name)
        self.stop_line_abs = abs(stop_line)
        self.warren_session = WarrenSession(name)

    def run(self):
        ...

    def start(self):
        threading.Thread(target=self.start_checking_stop_line).start()
        threading.Thread(target=self.run).start()

    def start_checking_stop_line(self):
        while True:
            details: Dict[str, stocks.StockDetail2] = {
                detail.code: detail for detail in
                stocks.get_details([holding.code for holding in self.wallet.holdings])
            }

            for holding in self.wallet.holdings:
                try:
                    detail = details.get(holding.code)
                    cur_price = detail.price
                    earnings_rate = calc.earnings_ratio(holding.price, cur_price)
                    if earnings_rate < -self.stop_line_abs or earnings_rate > self.stop_line_abs:
                        self.try_sell(code=holding.code,
                                      what=f'손익절 라인 {self.stop_line_abs}%',
                                      order_price=detail.bid)
                except:
                    self.logger.debug(traceback.format_exc())
                    self.logger.warning(f'Failed to get expected price for {holding.code}')

            time.sleep(60)

    def try_buy(self, code: str, what: str, order_price: int = None):
        if self.wallet.has(code):
            return

        if not order_price:
            detail = list(stocks.get_details([code]))[0]
            order_price = detail.ask

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

    def try_sell(self, code: str, what: str, order_price: int = None):
        if not self.wallet.has(code):
            return

        holding = self.wallet.get(code)

        if not order_price:
            detail = list(stocks.get_details([code]))[0]
            order_price = detail.bid

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


# 취급 코드들
available_codes = stocks.get_available()


def init_available_codes():
    global available_codes
    details: Dict[str, stocks.StockDetail2] = {
        detail.code: detail
        for detail in stocks.get_details(available_codes)
    }

    # 정배열만 필터링
    straights = []
    for code, detail in details.items():
        calculator = mas.get_calculator(detail.code)
        if calculator.is_straight(detail.price):
            straights.append(code)

    available_codes = straights
    for av_code in available_codes:
        print(av_code, details.get(av_code).name)


init_available_codes()


class Simulator_1(Simulator):
    """
    3번
    """

    def __init__(self):
        super().__init__('[3]골든_데드_크로스')

    def on_event(self, event: events.Event):
        # 골든/데드 크로스 아닌 이벤트는 무시
        if event.category in [44, 45]:
            return

        if event.code not in available_codes:
            return

        detail = list(stocks.get_details([event.code]))[0]
        ma_calc = mas.get_calculator(event.code)
        ma_20_cur = ma_calc.get(mas.MA.MA_20, cur_price=detail.price)
        ma_20_prv = ma_calc.get(mas.MA.MA_20, pos=-1)

        if event.category == 45 and ma_20_prv < ma_20_cur:
            # 골든크로스 & 어제_20MA < 현재_20MA < 현재가
            self.try_buy(code=event.code, what='[3-45]골든크로스', order_price=detail.ask)
        elif event.category == 44:
            self.try_sell(code=event.code, what='[3-46]데드크로스', order_price=detail.bid)

    def run(self):
        events.subscribe(self.on_event)
        events.start()

    def start(self):
        threading.Thread(target=self.start_checking_stop_line).start()
        self.run()


class Simulator_2(Simulator):
    """
    2번
    """

    def __init__(self):
        super().__init__('[2]5일선_상향돌파')

    def run(self):
        while True:
            self.logger.debug('# HEALTH CHECK #')
            details = stocks.get_details(available_codes)
            # 모든 취급 종목에 대해...
            for detail in details:
                # 5MA, 20MA 구한다
                ma_calc = mas.get_calculator(detail.code)
                ma_5 = ma_calc.get(mas.MA.MA_5, cur_price=detail.price)
                ma_20 = ma_calc.get(mas.MA.MA_20, cur_price=detail.price)

                if ma_20 < detail.open < ma_5 <= detail.price:
                    # 시가 < 5MA & 20MA < 5MA <= 현재가
                    self.try_buy(
                        code=detail.code,
                        what='[2]5일선_상향돌파',
                        order_price=detail.ask
                    )

            time.sleep(30)


class Simulator_3(Simulator):
    """
    1번
    """

    def __init__(self):
        super().__init__('[1]MA60_120_하방터치')

    def run(self):
        while True:
            self.logger.debug('# HEALTH CHECK #')

            # 취급 종목의 상세정보 구한다
            details = stocks.get_details(available_codes)
            for detail in details:
                # 본 종목의 60/120MA를 구한다
                ma_calc = mas.get_calculator(detail.code)
                ma_60 = ma_calc.get(mas.MA.MA_60, cur_price=detail.price)
                ma_120 = ma_calc.get(mas.MA.MA_120, cur_price=detail.price)

                if ma_60 <= detail.price <= ma_60 * 1.02:
                    self.try_buy(
                        code=detail.code,
                        what='[1]60MA_하방터치',
                        order_price=detail.ask
                    )
                elif ma_120 <= detail.price <= ma_120 * 1.02:
                    self.try_buy(
                        code=detail.code,
                        what='[1]120MA_하방터치',
                        order_price=detail.ask
                    )

            time.sleep(30)
