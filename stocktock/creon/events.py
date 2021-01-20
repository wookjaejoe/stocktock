import ctypes
import sys
from dataclasses import dataclass

import win32com.client
from PyQt5.QtWidgets import *

g_objCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')

assert ctypes.windll.shell32.IsUserAnAdmin(), '관리자 권한 필요'
assert g_objCpStatus.IsConnect != 0, 'CREON+ 연결 실패'

subscribers = []


@dataclass
class Event:
    category: int
    code: str
    time: int
    cancel: bool


def publish(category: int, code: str, time: int, cancel: bool):
    for subscriber in subscribers:
        subscriber(Event(category=category, code=code, time=time, cancel=cancel))


# CpEvent: 실시간 이벤트 수신 클래스
class CpEvent:
    def set_params(self, client, name, caller):
        self.client = client  # CP 실시간 통신 object
        self.name = name  # 서비스가 다른 이벤트를 구분하기 위한 이름
        self.caller = caller  # callback 을 위해 보관

    def OnReceived(self):
        # 실시간 처리 - marketwatch : 특이 신호(차트, 외국인 순매수 등)
        if self.name == 'marketwatch':
            code = self.client.GetHeaderValue(0)
            cnt = self.client.GetHeaderValue(2)

            for i in range(cnt):
                time = self.client.GetDataValue(0, i)
                update = self.client.GetDataValue(1, i)
                category = self.client.GetDataValue(2, i)
                cancel = update == ord('c')
                publish(category=category, code=code, time=time, cancel=cancel)

        # 실시간 처리 - marketnews : 뉴스 및 공시 정보
        elif self.name == 'marketnews':
            update = self.client.GetHeaderValue(0)
            delete = update == ord('D')
            code = self.client.GetHeaderValue(1)
            time = self.client.GetHeaderValue(2)
            category = self.client.GetHeaderValue(4)
            publish(category=category, code=code, time=time, cancel=delete)


class CpPublish:
    def __init__(self, name, serviceID):
        self.name = name
        self.obj = win32com.client.Dispatch(serviceID)
        self.bIsSB = False

    def Subscribe(self, var, caller):
        if self.bIsSB:
            self.Unsubscribe()

        if len(var) > 0:
            self.obj.SetInputValue(0, var)

        handler = win32com.client.WithEvents(self.obj, CpEvent)
        handler.set_params(self.obj, self.name, caller)
        self.obj.Subscribe()
        self.bIsSB = True

    def Unsubscribe(self):
        if self.bIsSB:
            self.obj.Unsubscribe()
        self.bIsSB = False


# CpPBMarkeWatch:
class CpPBMarkeWatch(CpPublish):
    def __init__(self):
        super().__init__('marketwatch', 'CpSysDib.CpMarketWatchS')


# CpPBMarkeWatch:
class CpPB8092news(CpPublish):
    def __init__(self):
        super().__init__('marketnews', 'Dscbo1.CpSvr8092S')


# CpRpMarketWatch : 특징주 포착 통신
class CpRpMarketWatch:
    def __init__(self):
        self.objStockMst = win32com.client.Dispatch('CpSysDib.CpMarketWatch')
        self.objpbMarket = CpPBMarkeWatch()
        self.objpbNews = CpPB8092news()
        return

    def Request(self, code, caller):
        self.objpbMarket.Unsubscribe()
        self.objpbNews.Unsubscribe()

        self.objStockMst.SetInputValue(0, code)
        # 1: 종목 뉴스 2: 공시정보 10: 외국계 창구첫매수, 11:첫매도 12 외국인 순매수 13 순매도
        categories = [44, 45, 46, 47, 58, 59]  # todo: externalize
        self.objStockMst.SetInputValue(1, ','.join([str(c) for c in categories]))
        self.objStockMst.SetInputValue(2, 0)  # 시작 시간: 0 처음부터
        self.objStockMst.BlockRequest()
        assert self.objStockMst.GetDibStatus() == 0, f'통신 상태({self.objStockMst.GetDibStatus()}) - {self.objStockMst.GetDibMsg1()}'
        count = self.objStockMst.GetHeaderValue(2)  # 수신 개수
        for i in range(count):
            time = self.objStockMst.GetDataValue(0, i)
            _code = self.objStockMst.GetDataValue(1, i)
            cate = self.objStockMst.GetDataValue(3, i)
            publish(category=cate, code=_code, time=time, cancel=False)

        self.objpbMarket.Subscribe(code, caller)
        self.objpbNews.Subscribe(code, caller)

        return True


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.objMarketWatch = CpRpMarketWatch()
        self.objMarketWatch.Request('*', self)


def subscribe(func):
    subscribers.append(func)


def start():
    app = QApplication(sys.argv)
    MyWindow()
    app.exec_()



