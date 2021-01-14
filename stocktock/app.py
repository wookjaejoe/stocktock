code = 'A000660'
# result = charts.request_ex(code, charts.ChartType.MINUTES)
# result = news.request(0)
# print()


# from simulator import *
# from creon import charts
# from creon import events_bak
#
# begin = datetime(2020, 12, 1)
# end = datetime(2020, 12, 2)
# chart = charts.request_by_count(code, charts.ChartType.MINUTES)
# events = events_bak.request()
# print()
#
# def on_data(now: datetime):
#     # todo: 뉴스 확인, 매수/매도
#     # todo: 매도 시 결과 확인
#     pass
#
#
# def main():
#     simulator = Simulator(
#         begin=begin,
#         end=end,
#         period=timedelta(minutes=1)
#     )
#     simulator.start(on_data)

from creon.events import *


def main():
    send_events()
    subscribe()
    while input('[종료: q]') != 'q':
        pass


if __name__ == '__main__':
    main()
