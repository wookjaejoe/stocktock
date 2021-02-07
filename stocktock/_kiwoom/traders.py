from pykiwoom.kiwoom import *

kiwoom = Kiwoom()
kiwoom.CommConnect(block=True)

# 주식계좌
accounts = kiwoom.GetLoginInfo("ACCNO")
stock_account = accounts[0]

SAMSUNG_CODE = "005930"


class Trader:
    @classmethod
    def buy(cls, code, count):
        # 삼성전자, 10주, 시장가주문 매수
        return kiwoom.SendOrder(rqname="시장가매수",
                                screen="0101",
                                accno=stock_account,
                                order_type=1,
                                code=code,
                                quantity=count,
                                price=0,
                                hoga="03",
                                order_no="")

    @classmethod
    def sell(cls, code, count):
        # 삼성전자, 10주, 시장가주문 매도
        return kiwoom.SendOrder(rqname="시장가매도",
                                screen="0101",
                                accno=stock_account,
                                order_type=2,
                                code=code,
                                quantity=count,
                                price=0,
                                hoga="03",
                                order_no="")
