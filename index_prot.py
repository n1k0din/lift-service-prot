from Timeseries import Timeseries
from datetime import datetime, timedelta
from collections import defaultdict, deque, namedtuple
from math import sqrt
import xml_parser
import csv
import oldy

record = namedtuple('record', ['dt', 'num'])

ONE_HOUR = timedelta(hours=1)
ONE_DAY = timedelta(days=1)

GAP = timedelta(minutes=120)

CHIPPER = ONE_DAY

WORKING_DAYS = 25
OFF_DAYS = 12

ROUND_H = {'minute': 0, 'second': 0, 'microsecond': 0}


LIFT = '1295'


def liftstats_from_list(lst: list, first_date: datetime, last_date: datetime, use_last=True) -> dict:
    lifts = {}
    for lift_id, dt, num in lst:
        if lift_id not in lifts:
            lifts[lift_id] = Timeseries(first_date, last_date, timedelta(hours=1), 'XXX')
        num = int(num)
        dt = dt[:13]
        dt = oldy.str_to_datetime(dt)  # это ускоряет обработку в 3 раза

        # в часе может быть несколько записей
        # add_abs
        # add_rel

        if use_last:  # мы или перезапишем последней
            lifts[lift_id][dt] = num
        else:
            if lifts[lift_id][dt] == 'XXX':  # значение по-умолчанию
                lifts[lift_id][dt] = num

    return lifts


def fill_dt_dict_with_x(dt_dict, x, from_dt, to_dt):
    t = from_dt
    while t < to_dt:
        dt_dict[t] = x
        t += ONE_HOUR
        # print(t, "to", x)


def add_abs_dirty(abs_dirty, dt, num):

    dtnum = record(dt, num)
    abs_dirty.append(dtnum)



    # dt_key = dt
    #
    # abs_dirty_dict[dt_key] = num
    #
    # prev_hour = dt_key - ONE_HOUR
    #
    # # нет смысла искать заполнение пропуска для первого значения в словаре
    # if dt_key != min(abs_dirty_dict) and prev_hour not in abs_dirty_dict:
    #     # найдем ближайшую запись с данными
    #     last = prev_hour
    #
    #     while last not in abs_dirty_dict and last > min(abs_dirty_dict) and last > dt_key - CHIPPER:
    #         last -= ONE_HOUR
    #
    #     if last in abs_dirty_dict:
    #
    #         # сначала проверим, стоял ли лифт во время пропусков
    #         if abs_dirty_dict[dt_key] == abs_dirty_dict[last]:
    #             filler = abs_dirty_dict[dt_key]
    #             fill_dt_dict_with_x(abs_dirty_dict, filler, last + ONE_HOUR, dt_key)
    #         elif dt_key - last > GAP:
    #             filler = None
    #             fill_dt_dict_with_x(abs_dirty_dict, filler, last + ONE_HOUR, dt_key)









def stats_from_list(lst: list):
    abs_stats = defaultdict(deque)
    rel_stats = {}
    for lift_id, dt, num in lst:
        num = int(num)
        #YYYY-mm-dd HH:MM:SS
        dt = dt[:16]
        dt = oldy.str_to_datetime(dt)

        add_abs_dirty(abs_stats[lift_id], dt, num)
        #add_rel(rel_stats[lift_id]), dt, num)

    return abs_stats


def minutes_timdelta(dt0: datetime, dt1: datetime) -> float:

    delta = dt1 - dt0 if dt1 > dt0 else dt0 - dt1
    return delta.seconds / 60


def add(t0, t1, res):
    dt0 = oldy.str_to_datetime(t0.dt)
    dt1 = oldy.str_to_datetime(t1.dt)
    print(dt0, dt1)

    if t1.num == t0.num:  # количество включений не изменилось
        # присваиваем часам с dt0.replace по dt1.replace
        # print("Заполнено предыдущим", t1, t0)
        # прикол - мы в любом случае знаем значение для предыдущего часа

        i = dt0.replace(**ROUND_H)
        while i <= dt1.replace(**ROUND_H):
            res[i] = res[dt0.replace(**ROUND_H)]
            i += ONE_HOUR

    else:
        # вариант номер раз: заполним пустышками
        if dt1 - dt0 >= GAP:
                print("Заполнено None", t1, t0)
                i = dt0.replace(**ROUND_H)
                while i <= dt1.replace(**ROUND_H):
                    res[i] = None
                    i += ONE_HOUR

        # вариант 2: аппроксимируем
        else:
            # F(th) = F1 - (t1 - th) * k, где k = (F(t1) - F(t0)) / (t1 - t0)
            interval = minutes_timdelta(dt1, dt0)
            k = (t1.num - t0.num) / interval
            # print("k = ", k)
            # print("interval = ", interval)
            th = dt1.replace(**ROUND_H)
            # print(th, dt1, "th - t1 = ", minutes_timdelta(dt1, th))
            res[th] = t1.num - k * minutes_timdelta(dt1, th)
            print(th, res[th], sep=';')


# проверяем, есть ли дырки в словаре с ключами-датавременем
def empty_test(d):
    start = min(d)
    stop = max(d)

    dt = start
    any_empty = False
    while dt < stop:
        if dt not in d:
            print("EMPTY", dt)
            any_empty = True
        dt += ONE_HOUR

    return any_empty


def read_stats():
    csv.register_dialect('win', delimiter=';')
    raw_stats = oldy.csvfile_to_list(LIFT+'.csv', 'win')  # читаем файл в список
    stats = iter(raw_stats)

    next = stats.__next__()
    t0 = record(next[1], int(next[2]))
    t0_hour = t0.dt[11:13]


    res = {}
    # Допущение - независимо от минуты в самом первом измерении, это значение записывается в res[час]

    res[oldy.str_to_datetime(t0.dt).replace(**ROUND_H)] = t0.num

    while True:
        try:
            next = stats.__next__()
            t1 = record(next[1], int(next[2]))
            t1_hour = t1.dt[11:13]
            while t1_hour == t0_hour:
                next = stats.__next__()
                t1 = record(next[1], int(next[2]))
                t1_hour = t1.dt[11:13]

            # print(t0.dt, t0.num, t1.dt, t1.num, '\n')
            add(t0, t1, res)

            t0 = t1
            t0_hour = t1_hour

        except StopIteration:
            break


    print("res start")
    for dt in sorted(res):
        print(dt, res[dt], sep=';')
    print(("res end"))

    return res




def get_bad_days(stats):
    bad_days = set()
    for dt in stats:
        if stats[dt] is None:
            bad_days.add((dt - ONE_HOUR).replace(hour=0))
            bad_days.add(dt.replace(hour=0))
    return bad_days


def split_days(firstday, lastday):
    """
    возвращает два списка - с буднями и выходными
    """
    holidays = xml_parser.parse_xml()

    working_days_list = []
    weekend_days_list = []
    day = firstday.replace(hour=0)
    while day < lastday:

        if day in holidays or day.weekday() in (5, 6):
            weekend_days_list.append(day)
        else:
            working_days_list.append(day)

        day += ONE_DAY

    return working_days_list, weekend_days_list


def get_another_day(stats, good_list, bad_list):
    i = max(stats).replace(hour=0) - ONE_DAY
    while i >= min(stats):
        # if i in good_list and i not in bad_list:
        if i in good_list and i not in bad_list:
            yield i
        #     print(i)
        #     yield i
        i -= ONE_DAY


def get_dayset(stats, good_list, bad_list, n_days):
    k = 0
    dayset = set()
    for day in get_another_day(stats, good_list, bad_list):
        dayset.add(day)
        k += 1
        if k >= n_days:
            return dayset
    return dayset


def print_table(dayset: set, stats):
    for day in sorted(dayset):
        print(day.strftime("%d.%m.%Y"), end=';')
        for i in range(24):
            dt = day.replace(hour=i)

            print(stats.get((dt + ONE_HOUR), 999) - stats.get(dt, -1), end=';')
        print()


def sum_table(dayset: set, stats):
    sum = 0
    for day in sorted(dayset):
        for i in range(24):
            dt = day.replace(hour=i)
            sum += (stats.get((dt + ONE_HOUR), 999) - stats.get(dt, -1))
    return sum


def calc_a(dayset, stats):
    a = defaultdict(int)
    for day in sorted(dayset):
        for i in range(24):
            dt = day.replace(hour=i)
            a[i] += (stats.get(dt + ONE_HOUR, stats[dt])-stats[dt])

    for x in a:
        a[x] /= len(dayset)

    return a


def calc_s(a):
    s = {}
    for key in a:
        s[key] = 3 * sqrt(a[key])

    return s


def calc_tm(a):
    tm = {}
    for key in a:
        tm[key] = a[key] - 3 * sqrt(a[key])

    return tm


def count_neg(iterable):
    sum = 0
    for x in iterable:
        if x < 0:
            sum += 1

    return sum


def calc_final(dayset, stats, tm, a):
    final = {}

    for day in sorted(dayset):
        for i in range(24):
            dt = day.replace(hour=i)
            num = (stats.get(dt + ONE_HOUR, stats[dt])-stats[dt])
            if num > tm[dt.hour]:
                final[dt] = num
            else:
                print(f"{dt} was {num} with tm={tm[dt.hour]:.2f} changed to {a[dt.hour]}")
                final[dt] = a[dt.hour]


    return final


def print_final(dayset, final):

    for day in sorted(dayset):
        i = day
        print(i.strftime("%d.%m.%Y"), end=';')
        while i < day + ONE_DAY:
            print(final[i], end=';')
            i += ONE_HOUR
        print()





def main():

    stats = read_stats()

    if empty_test(stats):
        return

    work, weekend = split_days(min(stats), max(stats))
    #print(work, '\n', weekend)
    #
    bad_days = get_bad_days(stats)
    # print("baddys")
    # for lift in bad_days:
    #     print(lift, bad_days[lift])
    #
    #
    work_dayset = get_dayset(stats, work, bad_days, WORKING_DAYS)

    offday_dayset = get_dayset(stats, weekend, bad_days, OFF_DAYS)

    print("WORK")
    print_table(work_dayset, stats)
    #
    print("OFF")
    print_table(offday_dayset, stats)
    #

    a_work = calc_a(work_dayset, stats)
    # print("A WORK")
    # for x in a_work:
    #     print(a_work[x], end=';')
    # print()

    a_off = calc_a(offday_dayset, stats)

    print(a_work, a_off, sep='\n')
    #
    tm_work = calc_tm(a_work)
    tm_off = calc_tm(a_off)
    #
    print(tm_work, tm_off, sep='\n')
    # for x in tm_work:
    #     print(tm_work[x], end=';')
    # print()
    #
    #
    neg = count_neg(tm_work.values()) + count_neg(tm_off.values())
    print("Отрицательных порогов: ", neg)
    if neg > (WORKING_DAYS + OFF_DAYS) / 2:
        print("Индекс равен *")
        return
    #
    print("work final")
    work_final = calc_final(work_dayset, stats, tm_work, a_work)
    print_final(work_dayset, work_final)
    #
    print("off final")
    off_final = calc_final(offday_dayset, stats, tm_off, a_off)
    print_final(offday_dayset, off_final)


    real_sum = sum_table(work_dayset, stats) + sum_table(offday_dayset, stats)
    final_sum = sum(work_final.values()) + sum(off_final.values())
    print(real_sum, final_sum, real_sum/final_sum, final_sum - real_sum)
    #index = calc_real(stats, work_dayset, offday_dayset) /



























if __name__ == '__main__':
    main()
