import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import *

import win32com.client

td_util = win32com.client.Dispatch('CpTrade.CpTdUtil')
stock_mst = win32com.client.Dispatch('DsCbo1.StockMst')
init_code = td_util.TradeInit()

objCpCodeMgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")
codeList = objCpCodeMgr.GetStockListByMarket(1)  # 거래소
codeList2 = objCpCodeMgr.GetStockListByMarket(2)  # 코스닥

init_codes = {
    -1: '오류',
    0: '정상',
    1: '업무 키 입력 잘못 됨',
    2: '계좌 비밀 번호 입력 잘못 됨',
    3: '취소'
}


# enum 주문 상태 세팅용
class OrderType(Enum):
    SELL = '1'  # 매도
    BUY = '2'  # 매수
    NONE = '3'


@dataclass
class Order:
    order_type: OrderType
    code: str
    count: int


assert init_code == 0, init_codes.get(init_code)


def get_price(code):
    stock_mst.SetInputValue(0, code)
    ret = stock_mst.BlockRequest()

    sells = []
    buys = []
    for i in range(10):
        sells.append(stock_mst.GetDataValue(0, i))  # 매도호가
        buys.append(stock_mst.GetDataValue(1, i))  # 매수호가

    return sells, buys


def _order(order_type: OrderType, code: str, price: int, count: int):
    acc = td_util.AccountNumber[0]  # 계좌번호
    accFlag = td_util.GoodsList(acc, 1)  # 주식상품 구분
    objStockOrder = win32com.client.Dispatch("CpTrade.CpTd0311")
    objStockOrder.SetInputValue(0, order_type.value)  # 1: 매도, 2: 매수
    objStockOrder.SetInputValue(1, acc)  # 계좌번호
    objStockOrder.SetInputValue(2, accFlag[0])  # 상품구분 - 주식 상품 중 첫번째
    objStockOrder.SetInputValue(3, code)  # 종목코드
    objStockOrder.SetInputValue(4, count)  # 매수수량
    objStockOrder.SetInputValue(5, price)  # 주문단가 - 필요한 가격으로 변경 필요
    objStockOrder.SetInputValue(7, "0")  # 주문 조건 구분 코드, 0: 기본 1: IOC 2:FOK
    objStockOrder.SetInputValue(8, "01")  # 주문호가 구분코드 - 01: 보통
    ret = objStockOrder.BlockRequest()

    # 만약 4를 리턴받은 경우는 15초동안 호출 제한을 초과한 경우로 잠시 후 다시 요청이 필요 합니다.
    # assert ret == 0, f'주문 요청 오류({ret})'  # 0: 정상,  그 외 오류, 4: 주문요청제한 개수 초과
    if ret == 4:
        time.sleep(30)
        _order(order_type, code, price, count)

    rqStatus = objStockOrder.GetDibStatus()
    errMsg = objStockOrder.GetDibMsg1()
    assert rqStatus == 0, f'주문 실패({rqStatus}) - {errMsg}'
    ### todo: 미체결 방어

    logging.info(f'ORDER COMPLETE - {order_type.value}, {code}, {price}, {count}')


def _buy(code: str, count: int):
    sells, _ = get_price(code)
    price = min(sells)
    _order(order_type=OrderType.BUY,
           code=code,
           price=price,
           count=count)


def _sell(code: str, count: int):
    _, buys = get_price(code)
    price = max(buys)
    _order(order_type=OrderType.SELL,
           code=code,
           price=price,
           count=count)


# 예약 주문 내역 조회 및 미체결 리스트 구하기
def order_list():
    acc = td_util.AccountNumber[0]  # 계좌번호
    accFlag = td_util.GoodsList(acc, 1)  # 주식상품 구분
    td_9065 = win32com.client.Dispatch("CpTrade.CpTd9065")
    td_9065.SetInputValue(0, acc)
    td_9065.SetInputValue(1, accFlag[0])
    td_9065.SetInputValue(2, 20)

    while True:  # 연속 조회로 전체 예약 주문 가져온다.
        td_9065.BlockRequest()
        assert td_9065.GetDibStatus() == 0, f'연결 오류({td_9065.GetDibStatus()})  {td_9065.GetDibMsg1()}'

        cnt = td_9065.GetHeaderValue(4)
        if cnt == 0:
            break

        for i in range(cnt):
            i1 = td_9065.GetDataValue(1, i)  # 주문구분(매수 또는 매도)
            i2 = td_9065.GetDataValue(2, i)  # 코드
            i3 = td_9065.GetDataValue(3, i)  # 주문 수량
            i4 = td_9065.GetDataValue(4, i)  # 주문호가구분
            i5 = td_9065.GetDataValue(6, i)  # 예약번호
            i6 = td_9065.GetDataValue(12, i)  # 처리구분내용 - 주문취소 또는 주문예정
            i7 = td_9065.GetDataValue(9, i)  # 주문단가
            i8 = td_9065.GetDataValue(11, i)  # 주문번호
            i9 = td_9065.GetDataValue(12, i)  # 처리구분코드
            i10 = td_9065.GetDataValue(13, i)  # 거부코드
            i11 = td_9065.GetDataValue(14, i)  # 거부내용
            print(i1, i2, i3, i4, i5, i6, i7, i8, i9, i10, i11)

        # 연속 처리 체크 - 다음 데이터가 없으면 중지
        if not td_9065.Continue:
            break


class Trader:

    def __init__(self):
        self.queue: List[Order] = []
        threading.Thread(target=self.start_consume).start()

    def request_order(self, order: Order):
        self.queue.append(order)

    def start_consume(self):
        while True:
            if self.queue:
                order = self.queue.pop()
                try:
                    if order.order_type == OrderType.BUY:
                        _buy(order.code, order.count)
                    elif order.order_type == OrderType.SELL:
                        _sell(order.code, order.count)
                except BaseException as e:
                    logging.warning(e)
            else:
                time.sleep(1)
