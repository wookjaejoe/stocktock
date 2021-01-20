from creon import charts
from creon import stocks
from database import DbManager
from datetime import datetime, timedelta
import csv


print('Fetching stocks...')
all_stocks = stocks.get_all(stocks.MarketType.EXCHANGE) + stocks.get_all(stocks.MarketType.KOSDAQ)

for category in DbManager.get_event_categories().find():
    category_name = category.get('name')
    category_id = category.get('_id')
    if category_id not in [46, 47]:
        continue

    event_list = [evt for evt in DbManager.get_events().find({'category_id': category.get('_id')})]
    for event in event_list:
        code = event.get('code')
        created = event.get('created')

        try:
            candles = charts.request_by_term(code,
                                             chart_type=charts.ChartType.MINUTES,
                                             begin=created-timedelta(minutes=30),
                                             end=created+timedelta(minutes=30))
            before = candles[-1].get('종가')
            after = candles[0].get('종가')
            features = [
                category_id,
                category_name,
                code,
                created,
                before,
                candles[int(len(candles) / 2)].get('종가'),
                after
            ]

            print(', '.join([str(feature) for feature in features]))
        except:
            print('WARN')
            pass

    print(f'{category_id}, {category_name}, {len(event_list)}')


    print()

    # for event in DbManager.get_events().find({'category_id': category.get('_id')}):
        # code = event.get('code')
        # print('Fetching chart...')
        # candles = charts.request_by_count(code, charts.ChartType.MINUTES)
        # size = len(candles)
        # idx = 0

# for category in event_categories:
#     database.DbManager.get_events().find({'category'})
#
# stock_chart = {}
# idx = 0
# for stock in all_stocks[:50]:
#     chart = charts.request_by_count(
#         code=stock.code,
#         chart_type=charts.ChartType.DAY,
#         count=3
#     )
#     stock_chart.update({stock.code: (chart.get('시가'), chart.get('종가'))})
#     idx += 1
#     print(f'{idx} / {len(all_stocks)}', end='\r')
#
# f = open('event_effect.csv', 'a+')
# for event in events:
#     chart = stock_chart.get(event.get('code'))
#
#     if not chart:
#         continue
#
#     candles = {}
#     for candle in chart:
#         candles.update({event.get('created').hour * 100 + event.get('created').minute: candle})
#
#     price_at_event = candles.get(event.get('time'))
#
#     row = event.get('created'), event.get('time'), event.get('category_id'), event.get('contents'), event.get('code'), \
#           chart.values()[0], price_at_event.get('종가'), chart[-1].get('종가')
#     # 이벤트 종류, 이벤트 내용, 종목 코드, 이벤트 30분 전 가격, 이벤트 당시 가격, 이벤트 30분 후 가격
#     print(row)
#     f.write(', '.join([str(s) for s in row]))
