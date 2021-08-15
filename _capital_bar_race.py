from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas
from pykrx import stock

from database import fundamental


@dataclass
class YearMonth:
    year: int
    month: int

    def next(self):
        year = self.year
        month = self.month
        month += 1
        if month > 12:
            year += 1
            month = 1

        return YearMonth(year, month)

    @classmethod
    def now(cls):
        today = date.today()
        return YearMonth(today.year, today.month)

    def is_after(self, other: YearMonth):
        return self.to_int() > other.to_int()

    def to_int(self):
        return 100 * self.year + self.month

    def __str__(self):
        return str(self.year) + '-{0:02d}'.format(self.month)


def group_by(l: list, grouping_key, sorting_key):
    result = {}
    for item in l:
        k = grouping_key(item)
        if k not in result:
            result.update({k: []})
        result.get(k).append(item)

    for k in result:
        result.get(k).sort(key=sorting_key)

    return result


def get_names_by_code(target_date: date):
    d = target_date
    while True:
        assert abs(target_date - d) < timedelta(days=30), 'Something wrong...'
        result = stock.krx.get_market_ticker_and_name(date=d.strftime('%Y%m%d'), market='ALL').to_dict()
        if not result:
            print('???')
            d += timedelta(days=1)
            continue

        return result


def main():
    from_ym = YearMonth(1996, 1)
    to_ym = YearMonth(2021, 7)
    ym = from_ym

    df = pandas.DataFrame()
    with fundamental.AllCapitalTable() as capital_table:
        while True:
            if ym.is_after(to_ym):
                break

            print(ym)
            capitals = capital_table.find_all_by_year_and_month(ym.year, ym.month)
            capitals_by_code = group_by(capitals, lambda x: x.code, lambda x: x.date)
            capitals = [capitals_by_code.get(code)[-1] for code in capitals_by_code]
            capitals.sort(key=lambda x: x.cap, reverse=True)
            capitals = capitals[:30]
            assert capitals, 'Something wrong...'

            names_by_code = get_names_by_code(capitals[0].date)
            blacklist = []
            for c in capitals:
                if c.code not in names_by_code:
                    print(f'[WARN] Cannot found name for {c.code}')
                    blacklist.append(c)

            for c in blacklist:
                capitals.remove(c)

            df = pandas.merge(
                df, pandas.DataFrame({str(ym): {names_by_code.get(c.code): int(c.cap / 10000_0000) for c in capitals}}),
                how="outer", left_index=True, right_index=True
            )

            ym = ym.next()

    df.fillna(0, inplace=True)
    df.to_csv('bar_race.csv')


if __name__ == '__main__':
    main()
