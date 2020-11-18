from Timeseries import Timeseries
import oldy
import csv
from datetime import timedelta, datetime

ROUND_H = {'minute': 0, 'second': 0, 'microsecond': 0}

ONE_HOUR = timedelta(hours=1)
ONE_DAY = timedelta(days=1)


def init_with_zero(ts: Timeseries):
    for dt in ts:
        ts[dt] = 0


def calc_ladder(ts: Timeseries, raw_stats: list):
    """
    вычисляет почасовую сумму включений датчиков
    """

    for str_datetime, _ in raw_stats:
        dt = oldy.str_to_datetime(str_datetime)

        dt = dt.replace(**ROUND_H)
        ts[dt] += 1


def ts_to_table(ts: Timeseries):

    start = ts.start
    stop = ts.stop

    n = 24 + 1
    ndays = (stop - start).days + 1
    k = ndays

    res = [["xxx"] * k for i in range(n)]

    res[0][0] = "date\\time"
    i = start
    k = 1
    while i < stop:
        res[0][k] = datetime.strftime(i, "%d.%m.%Y")
        i += ONE_DAY
        k += 1

    i = start
    k = 1
    while i < start + ONE_DAY:
        res[k][0] = datetime.strftime(i, "%H:%M")
        i += ONE_HOUR
        k += 1

    i = start
    k = 1
    while k < ndays:
        m = i + ONE_DAY
        j = 1
        while i < m:
            res[j][k] = ts[i]
            i += ONE_HOUR
            j += 1
        m = m + ONE_DAY
        k += 1

    return res


def print_res(res):
    for row in res:
        for elem in row:
            print(elem, end=';')
        print()


def res_to_csv(res: list, filename='res.csv'):
    with open(filename, "w+") as f:
        for row in res:
            for elem in row:
                f.write(str(elem))
                f.write(';')
            f.write('\n')



if __name__ == '__main__':
    csv.register_dialect('win', delimiter=';')
    date_format = "%Y.%m.%d %H:%M:%S"

    raw_stats = oldy.csvfile_to_list('lestnica_nik.csv', 'win')

    first, last = oldy.get_first_last_day(raw_stats, date_index=0)

    drivestat = Timeseries(first, last, timedelta(hours=1))  # ряд со статистикой включений двигателя
    init_with_zero(drivestat)

    calc_ladder(drivestat, raw_stats)

    res = ts_to_table(drivestat)

    res_to_csv(res)



    # oldy.print_ts(drivestat)




