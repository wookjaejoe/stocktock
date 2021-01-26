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


if __name__ == '__main__':
    ret = Trader.buy(SAMSUNG_CODE, 1)
    print(ret)
    # todo: 리턴값 확인... 리턴값에 주문번호가 있을 수 있다. 오류 처리도 가능할 수 있다.
    # Trader.sell(SAMSUNG_CODE, 1)
