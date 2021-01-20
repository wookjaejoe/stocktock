import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'stocktock'))

from creon import stocks, charts, _events

SAMSUNG_CODE = 'A005930'


class TestCases(unittest.TestCase):

    def test_stock(self):
        stock_list = stocks.get_all(stocks.MarketType.KOSDAQ)
        self.assertTrue(len(stock_list) > 0)

    def test_detail(self):
        detail = stocks.get_detail(SAMSUNG_CODE)
        self.assertTrue(detail.code == SAMSUNG_CODE)

    def test_trend(self):
        trend = list(stocks.get_trend(code=SAMSUNG_CODE))
        self.assertTrue(len(trend) > 0)

    def test_chart(self):
        assert charts.request_by_count(
            code='A005380',
            chart_type=charts.ChartType.MINUTES
        )
        assert charts.request_by_term(
            code='A005380',
            begin=datetime.now() - timedelta(days=1),
            chart_type=charts.ChartType.MINUTES
        )

    def test_event(self):
        _events.subscribe()
        evt_list = _events.get_events()
        print()

if __name__ == '__main__':
    unittest.main()
