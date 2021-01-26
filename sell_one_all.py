from creon import stocks
from creon import traders

ALL_STOCKS = stocks.get_all(stocks.MarketType.EXCHANGE) + stocks.get_all(stocks.MarketType.KOSDAQ)

for stock in ALL_STOCKS:
    print(stock.code, stock.name)
    try:
        order = traders.Order(
            order_type=traders.OrderType.SELL,
            code=stock.code,
            count=1
        )
    except BaseException as e:
        print(f'ERROR: {e}')
