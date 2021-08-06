from __future__ import annotations

import calendar
from datetime import date, timedelta

import pandas

import krx
from database import fundamental
from dataclasses import dataclass


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


def main():
    from_ym = YearMonth(1996, 1)
    to_ym = YearMonth.now()
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
            assert capitals
            df = pandas.merge(
                df, pandas.DataFrame({str(ym): {krx.get_name(c.code): c.cap for c in capitals}}),
                how="outer", left_index=True, right_index=True
            )

            ym = ym.next()

    df.to_csv('bar_race.csv')


if __name__ == '__main__':
    main()
