from typing import *

import jsons
from bson import json_util

from creon.charts import ChartData
from database import mongo

db = mongo.DbManager.get_daily_charts()


def find(**query) -> List[ChartData]:
    def load(item: dict) -> ChartData:
        return jsons.load(item, ChartData, object_hook=json_util.object_hook)

    return [load(found) for found in db.find(query)]


def insert_many(data: List[ChartData]):
    db.insert_many(jsons.dump(data, default=json_util.default))


def insert(data: ChartData):
    db.insert_one(jsons.dump(data, default=json_util.default))


def update(chart_data: ChartData):
    query = {
        'code': chart_data.code,
        'datetime': chart_data.datetime,
        'chart_type': chart_data.chart_type.name
    }

    if find(code=chart_data.code,
            datatime=chart_data.datetime,
            chart_type=chart_data.chart_type.name):
        return db.update(query, jsons.dump(chart_data, default=json_util.default))
    else:
        return db.insert_one(jsons.dump(chart_data, default=json_util.default))


def auto_update():
    from creon import stocks, charts

    # 각 종목에 대해
    for stock in stocks.ALL_STOCKS:
        # 새 차트 조회
        new_chart = charts.request(code=stock.code,
                                   chart_type=charts.ChartType.DAY,
                                   count=100)

        # DB 에서 해당 종목 차트 조회
        old_chart = find(
            code=stock.code
        )

        for chart_data in new_chart:
            if chart_data.datetime in [x.datetime for x in old_chart]:
                # 해당 일시 데이터 있으면, PASS
                pass
            else:
                # 해당 일시 데이터 없으면, 추가
                insert(chart_data)
