import creon.stocks as st
import creon.traders as tr


def get_holdings():
    with open('wallets/5MA_상향돌파.csv', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            split = line.split(',')
            yield split


def main():
    holdings = list(get_holdings())

    details = st.get_details([code for code, _, _ in holdings])
    details = {detail.code: detail for detail in details}

    for code, count, _ in holdings:
        price = details.get(code).price
        tr.sell(
            code=code,
            count=count,
            price=price
        )


if __name__ == '__main__':
    main()

    # 현재가 조회
    # 매도 주문
