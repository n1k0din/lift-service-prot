import csv
from collections import defaultdict
from datetime import datetime, timedelta
from Timeseries import Timeseries

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
    first = datetime.strptime(lst[0][date_index], date_format)
    last = datetime.strptime(lst[-1][date_index], date_format)

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
def stats_from_list(ts: Timeseries, lst: list, date_format: str):
    lifts = set()  # заодно вернем сет встретившихся лифтов, чтоб два раза не вставать
    for lift, dt, num in lst:
        lifts.add(lift)
        num = int(num)
        dt = (datetime.strptime(dt, date_format)).replace(microsecond=0, second=0, minute=0)
        ts[dt][lift] = num  # даже если значение уже было, нужно его перезаписать, т.к. в исходнике абсолютн. значение
    return lifts


def events_from_list(ts: Timeseries, lst: list, date_format: str):

    current = defaultdict(dict)  # словарь {лифт: {номер_неисправности: её актуальность}}

    for lift, dt, flag, num in lst:
        num = int(num)
        flag = int(flag)
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
def norm_ts(ts: Timeseries, lifts: set):
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
        if drivestat[j][lift] != 0:  # наткнулись на лифт с движением
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



def prepare_stats_defects():

    csv.register_dialect('win', delimiter=';')
    date_format = "%Y-%m-%d %H:%M:%S.%f"

    print("Читаем файл со статистикой...")
    raw_stats = csvfile_to_list('statdriv.csv', 'win')
    print("Получаем первый и последний день...")
    first, last = get_first_last_day(raw_stats, date_format)

    drivestat = Timeseries(first, last, timedelta(hours=1))  # ряд со статистикой включений двигателя
    init_with_dict(drivestat)

    print("Заполняем словарь статистики первичными данными...")
    lifts = stats_from_list(drivestat, raw_stats, date_format)  # заполняем данными, но могут быть пропуски

    print("Переводим в почасовую статистику и заполняем пропуски...")
    norm_ts(drivestat, lifts)  # переводим статистику в почасовую и заполняем пропуски None
    # в результате у нас словарь {datetime: {lift_id: num}}

    print("Читаем файл с событиями...")
    raw_events = csvfile_to_list('events.csv', 'win')  # first и last будем использовать те же, что и для вкл. ГП

    events = Timeseries(first, last, timedelta(hours=1))  # создаем ряд
    init_events(events, lifts)  # инициализируем {datetime : {lift : {num : }}}

    print("Заполняем словарь событий первичными данными...")
    events_from_list(events, raw_events, date_format)  # заполняем данными из raw_events

    print("Заполняем пропуски...")
    fill_events(events)  # заполняем пропуски

    print("Заполняем словарь дефектов...")
    defects = defects_from_events(events)  # словарь "в этот час у этого лифта есть хоть одна активная ошибка"

    return lifts, drivestat, defects


def print_statuses(ts: Timeseries):
    for dt in ts:
        for lift in ts[dt]:
            print(dt, lift, sep=';')

def write_statuses(ts: Timeseries, filename: str):
    with open(filename, 'w') as f:
        for dt in ts:
            for lift in ts[dt]:
                f.write("{};{}\n".format(dt, lift))




if __name__ == '__main__':

    tests = [1]
    res = []

    lifts, drivestat, defects = prepare_stats_defects()
    print("Всего лифтов", len(lifts))

    for test in tests:
        print("test = ", test)
        hourly = calc_statuses(timedelta(hours=test), lifts, drivestat, defects)
        daily = calc_not_moving_all_day(drivestat, lifts)
        write_statuses(hourly, "hourly.csv")
        write_statuses(daily, "daily.csv")
        #print_statuses(statuses)
        #print_statuses(daily)


































