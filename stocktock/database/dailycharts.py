import logging
import pickle
import threading
import time
from typing import *

import jsons
from bson import json_util

from creon import stocks, charts
from creon.charts import ChartData
from database import mongo

db = mongo.DbManager.get_daily_charts()


def find(**query):
    def load(item: dict) -> ChartData:
        return jsons.load(item, ChartData, object_hook=json_util.object_hook)

    for found in db.find(query):
        yield load(found)


def find_by_code(code: str):
    return find(code=code)


def insert_many(data: List[ChartData]):
    target = jsons.dump(data, default=json_util.default)
    db.insert_many(target)


class AutoUpdater:

    def __init__(self):
        self.finished = False
        self.queue = []
        self.cache = []

    def start(self):
        db.drop()
        threading.Thread(target=self.start_gathering).start()
        threading.Thread(target=self.start_inserting).start()

        while not self.finished:
            time.sleep(5)

    def start_gathering(self):
        num = 0
        for stock in stocks.ALL_STOCKS:
            num += 1
            logging.debug(f'[{num}/{len(stocks.ALL_STOCKS)}] Gathering and inserting charts for {stock.code}...')
            # 새 차트 조회
            chart = charts.request(code=stock.code,
                                   chart_type=charts.ChartType.DAY,
                                   count=150)

            self.cache.extend(chart)
            self.queue.extend(chart)

        self.finished = True
        logging.info('FINISHED: Gathering all charts.')

    def start_inserting(self):
        def do_insert():
            data, self.queue = self.queue, []
            if data:
                logging.debug(f'Inserting {len(data)} data...')
                insert_many(data)

        while not self.finished:
            do_insert()
            time.sleep(5)

        do_insert()
        logging.info('FINISHED: Inserting all charts into the database.')


def get_cahce_path():
    return f'.dailycharts.pickle'


def save_cache(data: List[ChartData]):
    with open(get_cahce_path(), 'wb') as f:
        pickle.dump(data, f)


def load_cache() -> List[ChartData]:
    with open(get_cahce_path(), 'rb') as f:
        return pickle.load(f)


def update():
    updater = AutoUpdater()
    updater.start()
