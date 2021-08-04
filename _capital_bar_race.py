import calendar
from datetime import date, timedelta

import pandas

import krx
from database import fundamental


def main():
    dates = []
    fromdate = date(1996, 1, 1)
    todate = date.today()
    tempd = fromdate
    while True:
        if tempd > todate:
            break

        last_day_of_month = calendar.monthrange(tempd.year, tempd.month)[1]
        if tempd == date(tempd.year, tempd.month, last_day_of_month):
            dates.append(tempd)
        tempd += timedelta(days=1)

    df = None
    with fundamental.AllCapitalTable() as capital_table:
        for d in dates:
            print(f'{d}\r')
            capitals = capital_table.find_all_at(d)
            capitals.sort(key=lambda x: x.cap, reverse=True)
            capitals = capitals[:30]
            if capitals:
                df2 = pandas.DataFrame(
                    {
                        d: {krx.get_name(c.code): c.cap for c in capitals}
                    },
                )

                if df is None:
                    df = df2
                else:
                    df = pandas.merge(df, df2, how="outer", left_index=True, right_index=True)

    df.to_csv('xxx.csv')


if __name__ == '__main__':
    main()
