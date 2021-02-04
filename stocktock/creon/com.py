import time
from enum import Enum
from typing import *

import win32com.client


def client(dispatch: str):
    return win32com.client.Dispatch(dispatch)


_cybos = client("CpUtil.CpCybos")
_stockcode = client("CpUtil.CpStockCode")
_codemgr = client("CpUtil.CpCodeMgr")


def cybos():
    return _cybos


def stockcode():
    return _stockcode


def codemgr():
    return _codemgr


def stockmst():
    return client("DsCbo1.StockMst")


def stockmst2():
    return client("DsCbo1.StockMst2")


def stockchart():
    return client("CpSysDib.StockChart")


class ReqType(Enum):
    TRADE = 0
    NON_TRADE = 1
    SUBSCRIBE = 2


def limit_safe(req_type: ReqType):
    """
    요청 제한 방어

    Usage:
    @limit_safe(req_type=ReqType.TRADE)
    def func(...): ...
        ...

    """
    assert isinstance(req_type, ReqType), 'Something wrong...'

    def decorator(func):
        assert isinstance(func, Callable), 'Something wrong...'

        def run(*arg, **kwargs):
            while not cybos().GetLimitRemainCount(req_type.value):
                # limit-remain-count 0이면, 1초 대기
                time.sleep(1)

            return func(*arg, **kwargs)

        return run

    return decorator
