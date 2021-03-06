from Timeseries import Timeseries
from datetime import datetime, timedelta
from collections import defaultdict, deque, namedtuple
from math import sqrt
import xml_parser
import csv
import oldy
import pytest

record = namedtuple('record', ['dt', 'num'])

ONE_HOUR = timedelta(hours=1)
ONE_DAY = timedelta(days=1)

GAP = timedelta(minutes=120)

CHIPPER = ONE_DAY

N_WORKING_DAYS = 25
N_OFF_DAYS = 12

ROUND_H = {'minute': 0, 'second': 0, 'microsecond': 0}
ROUND_D = {'hour': 0, 'minute': 0, 'second': 0, 'microsecond': 0}





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
    # print(dt0, dt1, dt1 - dt0, dt1 - dt0 >= GAP)

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
        if dt1 - dt0.replace(**ROUND_H) >= GAP:
                i = (dt0 + ONE_HOUR).replace(**ROUND_H)
                while i <= dt1.replace(**ROUND_H):
                    print("Заполнено None", i)
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
            # print(th, res[th], sep=';')


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


def read_stats(lift_input):

    raw_stats = oldy.csvfile_to_list(lift_input + '.csv', 'win')  # читаем файл в список
    stats = iter(raw_stats)

    next = stats.__next__()
    t0 = record(next[1], int(next[2]))
    t0_hour = t0.dt[11:13]

    # Допущение - независимо от минуты в самом первом измерении, это значение записывается в res[час]
    res = {oldy.str_to_datetime(t0.dt).replace(**ROUND_H): t0.num}

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


    # print("res start")
    # for dt in sorted(res):
    #     print(dt, res[dt], sep=';')
    # print(("res end"))

    return res


def get_bad_days(stats):
    bad_days = set()
    for dt in stats:
        if stats[dt] is None:
            bad_days.add((dt - ONE_HOUR).replace(hour=0))
            bad_days.add(dt.replace(hour=0))
    return bad_days


def days_from_dt0_to_dt1(dt0: datetime, dt1: datetime):
    days = set()
    i = dt0.replace(**ROUND_D)

    while i <= dt1.replace(**ROUND_D):
        days.add(i)
        i += ONE_DAY
    return days


def get_not_moving_days(stats, n_hours=12):
    not_moving = set()
    start = min(stats)
    stop = max(stats)

    i = start
    while i < stop:
        j = i + ONE_HOUR
        k = 0
        while stats[j] and stats[j] == stats[i] and j < stop:
            k += 1
            j += ONE_HOUR
        if k > 12:
            not_moving.update(days_from_dt0_to_dt1(i, j - ONE_HOUR))
        i = j

    return not_moving


# работает, перебирает дни, показывает с какого момента сколько часов подряд лифт не двигался
def __get_not_moving_lifts(stats, n_hours=12):
    not_moving = set()
    start = min(stats)
    stop = max(stats)

    day = start
    print("Ищем дни без движения 12 часов подряд")
    while day < stop:
        # print("День", day)

        hour = day
        while hour <= day + ONE_DAY:
            # print("Час", hour)
            current = hour + ONE_HOUR
            k = 0
            while stats[current] == stats[hour] and current <= day + ONE_DAY:
                k += 1
                current += ONE_HOUR
            if k > 0:
                print(f"Начиная с {hour} лифт не двигался {k} часов подряд.")

            hour = current

        day += ONE_DAY


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
        if i in good_list and i not in bad_list:
            yield i
        i -= ONE_DAY


def get_dayset(stats, good_list, bad_list, n_days):
    k = 0
    dayset = set()
    for day in get_another_day(stats, good_list, bad_list):
        dayset.add(day)
        k += 1
        if k >= n_days:
            return dayset
    return None


def print_table(dayset: set, stats):
    for day in sorted(dayset):
        print(day.strftime("%d.%m.%Y"), end=';')
        for i in range(24):
            dt = day.replace(hour=i)
            print(stats[dt + ONE_HOUR] - stats[dt], end=';')
            # print(stats.get((dt + ONE_HOUR), 999) - stats.get(dt, -1), end=';')
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
            num1 = stats[dt + ONE_HOUR]
            num0 = stats[dt]
            num = num1 - num0 if num1 >= num0 else num1
            a[i] += num

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


def calc_final(dayset, stats, tm, a, defects):
    final = {}

    for day in sorted(dayset):
        for i in range(24):
            dt = day.replace(hour=i)
            num = (stats.get(dt + ONE_HOUR, stats[dt])-stats[dt])
            if num >= tm[dt.hour]:
                final[dt] = num
            else:

                if defects.get(dt):
                    final[dt] = a[dt.hour]
                    print(f"{dt} was {num} with tm={tm[dt.hour]:.2f} changed to {a[dt.hour]}")
                else:
                    print(f"{dt} ниже порога({num} < {tm[dt.hour]}), но журналом не подтверждено.")
                    final[dt] = num


    return final


def print_final(dayset, final):

    for day in sorted(dayset):
        i = day
        print(i.strftime("%d.%m.%Y"), end=';')
        while i < day + ONE_DAY:
            print(final[i], end=';')
            i += ONE_HOUR
        print()


def events_from_list(lst: list):
    events = {}

    current = {}

    for _, dt, flag, num in lst:
        num = int(num)
        flag = int(flag)
        dt = (oldy.str_to_datetime(dt)).replace(second=0, minute=0)

        if oldy.is_defect_start(num, flag):
            current[num] = True
        elif oldy.is_defect_stop(num, flag):
            current[num] = False

        #print(dt, lift)
        events[dt] = current.copy()

    return events


# events это временной ряд, значения = лифты (значения = коды ошибок (значения равно состояния ошибок)))
def fill_events(events: dict):

    i = min(events) + ONE_HOUR
    while i <= max(events):
        # print(i, events.get(i))
        if not events.get(i):  # и проверяем пустоту записей
            j = i - ONE_HOUR
            flag = False
            while j >= min(events):  # найдем какой-нибудь непустой статус
                # print('get_j = ', events.get(j))
                if events.get(j) is not None:
                    flag = True
                    break
                j -= ONE_HOUR

            if flag:  # нашли
                events[i] = events[j].copy()

        i += ONE_HOUR


def defects_from_events(events: dict):
    defects = {}

    for dt in events:
        defects[dt] = any(events[dt].values())

    return defects


def read_events(lift_input):
    raw_events = oldy.csvfile_to_list('e_' + lift_input + '.csv', 'win')

    events = events_from_list(raw_events)  # переписали что дали в словарь

    fill_events(events)  # заполнили пропуски

    return defects_from_events(events)


def main(lift_input):

    csv.register_dialect('win', delimiter=';')

    stats = read_stats(lift_input)  # возвращает недырявый словарь {дата_время: колво_включений}

    if empty_test(stats):
        return "EMPTY"

    defects = read_events(lift_input)  # возвращает словарь {дата_время: была_ли_активная_неисправность_по_журналу}
    print(f"Насобирали словарь дефектов с {min(defects)} по {max(defects)}")
    if empty_test(defects):
        return "EMPTY DEFECTS"


    work, weekend = split_days(min(stats), max(stats))

    not_moving = get_not_moving_days(stats)
    print(f"{len(not_moving)} дней без движения по 12 часов подряд: {not_moving}")

    bad_days = get_bad_days(stats)  # набор дней с пропусками в данных
    print(f"{len(bad_days)} дней с пропусками в данных: {bad_days}")

    bad_days.update(not_moving)
    print(f"Итого убираем из рассмотрения дней: {len(bad_days)}")

    # теперь из входных данных и списка рабочих/нерабочих дней собираем по сколько надо
    # тут неплохо смотрелось бы пересечение множеств, но важен порядок
    work_dayset = get_dayset(stats, work, bad_days, N_WORKING_DAYS)
    offday_dayset = get_dayset(stats, weekend, bad_days, N_OFF_DAYS)

    if not work_dayset or not offday_dayset:
        print("Не набралось достаточно дней!")
        return "OUTOFDAYS"

    print("WORK")
    print_table(work_dayset, stats)
    #
    print("OFF")
    print_table(offday_dayset, stats)
    #

    # средние
    a_work = calc_a(work_dayset, stats)
    a_off = calc_a(offday_dayset, stats)
    print(a_work, a_off, sep='\n')

    # пороги
    tm_work = calc_tm(a_work)
    tm_off = calc_tm(a_off)
    print(tm_work, tm_off, sep='\n')

    neg_work = count_neg(tm_work.values())
    neg_off = count_neg(tm_off.values())
    print("Отрицательных порогов: ", neg_work, neg_off)
    if neg_work >= 12 or neg_off >= 12:
        print("Мало поездок в день, индекс равен *")
        return "MANYNEG"

    print("work final")
    work_final = calc_final(work_dayset, stats, tm_work, a_work, defects)
    print_final(work_dayset, work_final)

    print("off final")
    off_final = calc_final(offday_dayset, stats, tm_off, a_off, defects)
    print_final(offday_dayset, off_final)

    real_sum = sum_table(work_dayset, stats) + sum_table(offday_dayset, stats)
    final_sum = sum(work_final.values()) + sum(off_final.values())
    index = real_sum / final_sum
    print(real_sum, final_sum, index)

    return index


if __name__ == '__main__':

    tests = ['3239', '3240', '3241', '3242', '1290', '1291', '1293', '1294', '1295', '2010']
    # tests = ['1295']
    res = []
    for test in tests:
        print(f'-----Тест {test}-----')
        res.append((test, main(test)))

    print("-----Общие результаты-----")
    for t, r in res:
        print(t, r)

