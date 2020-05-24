import csv
from collections import defaultdict
from datetime import datetime, timedelta
from Timeseries import Timeseries
import slow_daily

num_with_flags = {132, 145, 147, 149, 160, 161, 162, 164, 176, 144, 181}  # нужно учесть флаг для определения начала
num_wo_flag = {19: 18}  # ключ: событие-начало, значение: событие-конец

one_hour = timedelta(hours=1)


def is_defect_start(num: int, flag: int):
    return (num in num_wo_flag) or (num in num_with_flags and flag & 2 != 0)


def is_defect_stop(num: int, flag: int):
    return (num in num_wo_flag.values()) or (num in num_with_flags and flag & 2 == 0)


# читает csv файл с определенным диалектом в список, игнорирует первую строку
def csvfile_to_list(filename: str, dialect='excel'):
    raw_data = []
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, dialect=dialect)
        _ = reader.__next__()
        for row in reader:
            raw_data.append(row)
        return raw_data


# ВНИМАНИЕ! Список может оказаться несортированым, тогда нужно брать не ласт, а макс!
# на входе сортированный список строк, формат датывремени, номер столбца с датойвременем
# на выходе первый и последний день в виде datetime
def get_first_last_day(lst: list, date_format: str, date_index=1):
    dt_first = lst[0][date_index][:13]
    dt_last = lst[-1][date_index][:13]
    first = datetime.strptime(dt_first, date_format)
    last = datetime.strptime(dt_last, date_format)

    to_day_params = {'microsecond': 0, 'second': 0, 'minute': 0, 'hour': 0}

    first = first.replace(**to_day_params)
    last = last.replace(**to_day_params)
    last += timedelta(days=1)
    #last = last.replace(day=last.day)

    return first, last


def init_with_dict(ts: Timeseries):
    for dt in ts:
        ts[dt] = dict()


def init_with_dict_fromkeys(ts: Timeseries, keys: set):
    for dt in ts:
        ts[dt] = dict.fromkeys(keys)


def init_events(events: Timeseries, lifts: set):
    init_with_dict_fromkeys(events, lifts)
    for dt in events:
        for lift in events[dt]:
            events[dt][lift] = dict.fromkeys(num_with_flags | num_wo_flag.keys())


# заполняет временной ряд статистики включений главного привода
def stats_from_list(ts: Timeseries, lst: list, date_format: str, use_last=True):
    lifts = set()  # заодно вернем сет встретившихся лифтов, чтоб два раза не вставать
    for lift, dt, num in lst:
        lifts.add(lift)
        num = int(num)
        dt = dt[:13]
        dt = (datetime.strptime(dt, date_format)).replace(microsecond=0, second=0, minute=0)
        # в часе может быть несколько записей

        if use_last:  # мы или перезапишем последней
            ts[dt][lift] = num
        else:
            if lift not in ts[dt]:
                ts[dt][lift] = num

    return lifts


def events_from_list(ts: Timeseries, lst: list, date_format: str):

    current = defaultdict(dict)  # словарь {лифт: {номер_неисправности: её актуальность}}

    for lift, dt, flag, num in lst:
        num = int(num)
        flag = int(flag)
        dt = dt[:13]
        dt = (datetime.strptime(dt, date_format)).replace(microsecond=0, second=0, minute=0)

        if is_defect_start(num, flag):
            current[lift][num] = True
        elif is_defect_stop(num, flag):
            current[lift][num] = False

        #print(dt, lift)
        ts[dt][lift] = current[lift].copy()


def is_all_none(iterable):
    for elem in iterable:
        if elem is not None:
            return False
    return True


# events это временной ряд, значения = лифты (значения = коды ошибок (значения равно состояния ошибок)))
def fill_events(ts: Timeseries):
    one_hour = timedelta(hours=1)
    for dt in ts:  # перебираем даты
        for lift in ts[dt]:  # потом лифты
            if is_all_none(ts[dt][lift].values()):  # и проверяем, есть
                i = dt - one_hour
                flag = False
                while i >= ts.start:  # найдем какой-нибудь непустой статус
                    try:
                        if not is_all_none(ts[i][lift].values()):
                            flag = True
                            break
                    except:
                        # лифты из статистики и событий могут не совпадать
                        # print('Warning at ', i, lift)
                        pass
                    i -= one_hour


                if flag:  # нашли
                    ts[dt][lift].update(ts[i][lift])


# на случай если в самой первой записи статистики будут не все лифты
def init_first_row(ts: Timeseries, lifts: set):
    for lift in lifts:
        if lift not in ts[ts.start]:
            ts[ts.start][lift] = 0


# преобразует абсолютное кол-во включений в почасовое
def ts_to_relative(ts: Timeseries, lifts: set):
    init_first_row(ts, lifts)
    prev = ts[ts.start].copy()

    for dt in ts:
        for lift in lifts:
            if lift in ts[dt]:
                current = ts[dt][lift]
                # абсолютный счётчик может начаться заново в исходнике, тогда нужна не разница, а новое знач. счётчика
                ts[dt][lift] = current - prev[lift] if current >= prev[lift] else current
                prev[lift] = current
            else:
                # ну и записи просто может не быть
                ts[dt][lift] = None


# на входе Timeseries {дата: {лифт : {неисправность : активность неисправности}}}
# вернем Timeseries {дата: {лифт : есть хоть одна активная неисправность}}
def defects_from_events(events: Timeseries):
    defects = Timeseries(events.start, events.stop, timedelta(hours=1))
    init_with_dict(defects)

    for dt in events:
        for lift in events[dt]:
            defects[dt][lift] = any(events[dt][lift].values())

    return defects


def calc_statuses(delta: timedelta, lifts: set, drivestat: Timeseries, defects: Timeseries):
    first = drivestat.start
    last = drivestat.stop

    statuses = Timeseries(first, last, timedelta(hours=1))
    init_with_dict(statuses)
    one_hour = timedelta(hours=1)

    i = first + delta
    while i < last:  # перебираем дата-время от начала до конца по часам

        # хотим определить, сколько лифтов неисправно в этот час
        # неисправно = не двигался и была ошибка
        for lift in lifts:  # перебираем лифты
            if not is_moving(drivestat, lift, i, delta):  # лифт не двигался в отрезке [i-delta + 1; i]

                k = i - one_hour  # зафиксированное недвижение лифта в час i означает неработу лифта в час i - 1

                if is_errors(defects, lift, k, delta):  # и были активные ошибки
                    statuses[k][lift] = False  # отмечаем лифт как неисправный
        i += one_hour

    return statuses


# а были бы у нас абсолютные значения, мы бы просто сравнили первый и последний час
def calc_not_moving_all_day(drivestat: Timeseries, lifts: set ):
    one_day = timedelta(days=1)
    daily = Timeseries(drivestat.start, drivestat.stop, one_day)
    init_with_dict(daily)
    i = drivestat.start + one_day
    while i < drivestat.stop:
        for lift in lifts:
            if not is_moving(drivestat, lift, i, one_day):  # лифт не двигался в отрезке [i-delta + 1; i]
                k = i - one_day
                daily[k][lift] = False
        i += one_day
    return daily


# функция возвращает True если lift ДВИГАЛСЯ во временном отрезке [i - delta + 1; i]
def is_moving(drivestat: Timeseries, lift: str, i: datetime, delta: timedelta):
    j = i
    while j > i - delta:  # идем по периоду delta
        if drivestat[j][lift] != 0:  # наткнулись на лифт с движением TODO: None тоже движение чтоли?
            return True
        j -= one_hour
    return False


# функция возвращает True если на lift были активные неисправности во временном отрезке [i - delta + 1; i]
def is_errors(defects: Timeseries, lift: str, i: datetime, delta: timedelta):
    j = i
    while j > i - delta:
        if defects[j][lift]:
            return True
        j -= one_hour
    return False


# возвращает словарь с данными, когда лифт не работал = не двигался N часов в сутки
# есть похожая функция -||- -||- -||-                 = не двигался целые сутки
def calc_not_moving_n_hours_a_day(drivestat: Timeseries, lifts: set, n: int):
    one_day = timedelta(days=1)
    daily = Timeseries(drivestat.start, drivestat.stop, one_day)
    init_with_dict(daily)

    # у нас словарь {datetime: {lift_id: num}}
    # и где-то есть функция, которая по 25 значениям определяет, сколько часов в сутки работал лифт
    #  будем перебирать дни
    #   внутри будем перебирать часы
    #       генерим вот такой словарь { lift: [0, 1, 2, .., 24, 0] }
    #   теперь скармливаем по очереди списки из этого словаря нашей функции, она вернет список часов неработы
    #   мы их посчитаем, сравним с n и запишем результат в daily

    i = drivestat.start + one_day
    while i < drivestat.stop:
        j = i - one_day
        d = defaultdict(list)
        while j < i + one_hour:
            for lift in lifts:
                d[lift].append(drivestat[j][lift])

            j += one_hour
        # print(d)  # это словарь с данными за день i - one_day

        for lift, lst in d.items():
            r = slow_daily.foo(lst)
            n_not_moving = len(list(slow_daily.is_false(r)))
            if n_not_moving >= n:
                daily[i - one_day][lift] = False

        i += one_day

    return daily


def get_day_dict(drivestat: Timeseries, lifts: set, offset=0):
    one_day = timedelta(days=1)
    offset = timedelta(hours=offset)

    i = drivestat.start + one_day + offset
    while i < drivestat.stop:

        j = i - one_day
        # print("viewing from", j)
        d = defaultdict(list)
        while j < i + one_hour:
            for lift in lifts:
                d[lift].append(drivestat[j][lift])

            j += one_hour

        #print("Y", i - one_day, d.keys())

        # print("to", j - one_hour)
        yield (i - one_day - offset, d)

        i += one_day
        # print(d)  # это словарь с данными за день i - one_day

def count_false(d, in_a_row=False):
    sum = 0
    for k in sorted(d, reverse=True):
        if d[k] is False:
            sum += 1
        elif in_a_row:
            break
    return sum

def get_daily(ts: Timeseries, lifts: set, n: int, offset=0, in_a_row=False):

    one_day = timedelta(days=1)
    daily = Timeseries(ts.start, ts.stop, one_day)
    init_with_dict(daily)

    for k, d in get_day_dict(ts, lifts, offset):
        for lift, lst in d.items():
            r = slow_daily.foo(lst)

            n_not_moving = count_false(r, in_a_row)

            if n_not_moving >= n:
                # print("is false", k, lift)
                daily[k][lift] = False
    return daily






# в разработке!
# лифт неисправен сутки, если он неисправен все 24 часа в сутках
def calc_daily_statuses(statuses: Timeseries, lifts: set):
    oneday = timedelta(days=1)
    onehour = timedelta(hours=1)
    daily = Timeseries(statuses.start, statuses.stop, oneday)

    calc_one_day_statuses(datetime(2019, 12, 9), statuses, lifts)

    for day in daily:
        pass


# в разработке!
def calc_one_day_statuses(day: datetime, statuses: Timeseries, lifts: set):
    one_day = timedelta(days=1)
    one_hour = timedelta(hours=1)
    day_dict = dict.fromkeys(lifts, False)

    cur_hour = day
    for lift in lifts:

        while cur_hour < day + one_day:

            if lift not in statuses[cur_hour] or statuses[cur_hour][lift]:
                day_dict[lift] = True
                break
            cur_hour += one_hour


def fill_with_none(ts, lifts):
    for dt in ts:
        for lift in lifts:
            if lift not in ts[dt]:
                ts[dt][lift] = None


def prepare_stats_defects():

    csv.register_dialect('win', delimiter=';')
    #date_format = "%Y-%m-%d %H:%M:%S.%f"
    date_format = "%Y-%m-%d %H"

    print("Читаем файл со статистикой...")
    raw_stats = csvfile_to_list('statdriv.csv', 'win')
    print("Получаем первый и последний день...")
    first, last = get_first_last_day(raw_stats, date_format)

    drivestat = Timeseries(first, last, timedelta(hours=1))  # ряд со статистикой включений двигателя
    init_with_dict(drivestat)

    print("Заполняем словарь статистики первичными данными...")
    lifts = stats_from_list(drivestat, raw_stats, date_format, use_last=False)  # заполняем данными, но могут быть пропуски

    print("Устанавливаем пропуски в None...")
    fill_with_none(drivestat, lifts)  # заполняет пропуски None

    #print("Переводим в почасовую статистику и заполняем пропуски...")
    #ts_to_relative(drivestat, lifts)  # переводим статистику в почасовую и заполняем пропуски None
    # в результате у нас словарь {datetime: {lift_id: num}}

    #!print("Читаем файл с событиями...")
    #!raw_events = csvfile_to_list('events.csv', 'win')  # first и last будем использовать те же, что и для вкл. ГП

    #!events = Timeseries(first, last, timedelta(hours=1))  # создаем ряд
    #!init_events(events, lifts)  # инициализируем {datetime : {lift : {num : }}}

    #!print("Заполняем словарь событий первичными данными...")
    #!events_from_list(events, raw_events, date_format)  # заполняем данными из raw_events

    #!print("Заполняем пропуски...")
    #!fill_events(events)  # заполняем пропуски

    #!print("Заполняем словарь дефектов...")
    #!defects = defects_from_events(events)  # словарь "в этот час у этого лифта есть хоть одна активная ошибка"

    return lifts, drivestat, None


def print_statuses(ts: Timeseries):
    for dt in ts:
        for lift in ts[dt]:
            print(dt, lift, sep=';')

def write_statuses(ts: Timeseries, filename: str):
    with open(filename, 'w') as f:
        for dt in ts:
            for lift in ts[dt]:
                f.write("{};{}\n".format(dt, lift))


# метод 0 = лифт сломан, если не двигался n часов в сутки
# метод 1 = лифт сломан, если не двигался подряд последние n часов в сутки
# метод 2 = лифт сломан, если не двигался подряд последние n часов, смещение offset часов от начала суток
def calc_daily(method=0, **kwargs):
    drivestat = kwargs['drivestat']
    lifts = kwargs['lifts']

    if method == 0:
        n = kwargs['n']
        return get_daily(drivestat, lifts, n=n)

    if method == 1:
        n = kwargs['n']
        return get_daily(drivestat, lifts, n=n, in_a_row=True)

    if method == 2:
        n = kwargs['n']
        offset = kwargs['offset']
        return get_daily(drivestat, lifts, n=n, in_a_row=True, offset=offset)





if __name__ == '__main__':

    tests = [
             {'method': 2, 'n': 14, 'offset': 8},
             {'method': 2, 'n': 16, 'offset': 8}
             ]

    res = []

    lifts, drivestat, defects = prepare_stats_defects()
    print("Всего лифтов", len(lifts))

    for test in tests:
        print("test = ", test)
        #!hourly = calc_statuses(timedelta(hours=test), lifts, drivestat, defects)
        #!daily = calc_not_moving_(drivestat, lifts)  # это упрощенная версия calc_statuses
        daily = calc_daily(drivestat=drivestat, lifts=lifts, **test)  # это упрощенная версия calc_statuses
        res.append(daily)

    for i in range(len(res)):
        filename = str(i)+'_daily.csv'
        print("Сохраняем", filename, "...")
        write_statuses(res[i], filename)

    #!write_statuses(hourly, "hourly.csv")
    #write_statuses(daily, "daily.csv")
    #print_statuses(statuses)
    #print_statuses(daily)



































