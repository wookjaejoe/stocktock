from datetime import date, timedelta

import database.candles.minute as db
from creon import charts as creon_charts
from creon import stocks as creon_stocks


def update_stocks():
    cover_days: int = 1000
    for code in creon_stocks.get_availables():
        code = code[-6:]
        name = creon_stocks.get_name(code)

        # 종목 상세 정보 업데이트
        stock = db.Stock.find_by_code(code)
        if stock:
            stock.update(name=name)
        else:
            # 종목 업데이트
            db.Stock(code=code, name=name).insert()

        # 일봉 업데이트
        begin = date.today() - timedelta(days=cover_days)
        end = date.today()
        stock_id = db.Stock.find_by_code(code).id
        for candle in creon_charts.request_by_term(code=code, chart_type=creon_charts.ChartType.DAY,
                                                   begin=begin, end=end):
            exists = db.DayCandle.exists(stock_id=stock_id, date=candle.date, time=candle.time)
            if not exists:
                db.DayCandle(
                    stock_id=stock_id,
                    date=candle.date,
                    open=candle.open,
                    close=candle.close,
                    low=candle.low,
                    high=candle.high
                ).insert(do_commit=True)


def update_minute_candles(stock: db.Stock):
    cover_days: int = 800

    begin = date.today() - timedelta(days=cover_days)
    end = date.today()

    cur_date = begin
    while cur_date <= end:
        # 2주치 분봉 캔들 조회
        chart = creon_charts.request_by_term(
            code=stock.code,
            chart_type=creon_charts.ChartType.MINUTE,
            begin=cur_date,
            end=cur_date + timedelta(days=14)
        )

        for i in range(14):
            cur_date += timedelta(days=i)
            # 해당 일자 분봉 캔들 없으면, 하루 치 삽입
            if not db.MinuteCandle.exists(stock_id=stock.id, date=cur_date):
                db.MinuteCandle.insert_many([db.MinuteCandle(
                    stock_id=stock.id,
                    date=candle.date,
                    time=candle.time,
                    open=candle.open,
                    close=candle.close,
                    low=candle.low,
                    high=candle.high
                ) for candle in chart if candle.date == cur_date])

        cur_date += timedelta(days=1)


def main():
    update_stocks()


if __name__ == '__main__':

    while True:

        main()

