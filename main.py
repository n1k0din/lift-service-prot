import csv
from collections import defaultdict
from datetime import datetime, timedelta

num_with_flags = {132, 145, 147, 149, 160, 161, 162, 164, 176, 144, 181}  # нужно учесть флаг для определения начала
num_wo_flag = {19: 18}  # ключ: событие-начало, значение: событие-конец

start_date = datetime(2019, 12, 1)
stop_date = datetime(2019, 12, 21)


def norm_num(d):
    """
    Перебираем словарь с ключами-датами и делаем из абсолютный значений относительные
    """
    min_date = min(d)  # минимальный ключ = самая ранняя дата
    prev_abs_num = d[min_date]
    for dt in sorted(d):
        cur_abs_num = d[dt]
        d[dt] -= prev_abs_num
        prev_abs_num = cur_abs_num


# определяет, является ли событие индикатором неисправности
def is_defect(num: int, flag: int):
    return is_defect_start(num, flag) or is_defect_stop(num, flag)


def is_defect_start(num: int, flag: int):
    return (num in num_wo_flag) or (num in num_with_flags and flag & 2 != 0)


def is_defect_stop(num: int, flag: int):
    return (num in num_wo_flag.values()) or (num in num_with_flags and flag & 2 == 0)


def make_defect_statuses_dict(filename='Events.csv'):
    """
    Изменим логику. Сначала создадим словарь статусов дефектов:
    (лифт, дата) : {номер неисправности : bool}
    """
    # {лифт: {номер неисправности : bool}}

    current = defaultdict(dict)

    with open(filename, 'r') as csv_file:
        reader = csv.reader(csv_file, dialect='win')
        _ = reader.__next__()  # игнорим первую строку
        defect_statuses_dict = dict()

        for id_lift, dt, flag, num, _ in reader:

            num = int(num)
            flag = int(flag)
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f")  # преобразуем в datetime

            dt = dt.replace(second=0, minute=0)  # округлим до часа

            key = (dt, id_lift)

            if is_defect_start(num, flag):
                current[id_lift][num] = True
            elif is_defect_stop(num, flag):
                current[id_lift][num] = False

            defect_statuses_dict[key] = current[id_lift].copy()
            # print(key, defect_statuses_dict[key])

    return defect_statuses_dict


def fill_spaces(d, lifts: set):
    # на входе словарь (лифт, дата) : {номер неисправности : bool}

    i = start_date

    while i < stop_date:

        for lift in lifts:
            statuses = d.get((i, lift))
            if not statuses:
                # если в статусах пусто, надо найти предыдущее значение
                #print((i, lift), defects, sep = '*')
                j = i - timedelta(hours=1)
                flag = False
                while j >= start_date:
                    if d.get((j, lift)):
                        flag = True
                        break
                    j = j - timedelta(hours=1)

                if flag:
                    d[i, lift] = d[j, lift]
                else:
                    d[i, lift] = {}

        i += timedelta(hours=1)
    return d

def make_defects_from_statuses(d):
    # на входе словарь (лифт, дата) : {номер неисправности : bool}
    # на выходе словарь дефектов (лифт, дата) : True если дефект
    defects_dict = defaultdict(lambda: False)  # по умолчанию - НЕ дефект, т.е. всё хорошо
    for k in d:
        defects_dict[k] = any(d[k].values())
    return defects_dict


def make_defects_dict(filename='Events.csv'):
    """
    На входе файл, на выходе словарь
    словарь дефектов {(лифт, дата) : True если дефект}
    """
    with open(filename, 'r') as csv_file:
        reader = csv.reader(csv_file, dialect='win')
        _ = reader.__next__()  # игнорим первую строку

        defects_dict = defaultdict(lambda: False)  # по умолчанию - НЕ дефект, т.е. всё хорошо
        for id_lift, dt, flag, num, _ in reader:
            num = int(num)
            flag = int(flag)
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f")  # преобразуем в datetime

            dt = dt.replace(second=0, minute=0)  # округлим до часа

            if is_defect(num, flag):  # если событие ошибочное
                if not defects_dict[dt, id_lift]:  # а в словаре дефет не отмечен
                    defects_dict[dt, id_lift] = True  # отметим

        return defects_dict







def process(t_stat=1, t_events=1):

    csvfile = open('StatDriv.csv', 'r')
    csv.register_dialect('win', delimiter=';' )
    reader = csv.reader(csvfile, dialect="win")
    _ = reader.__next__()
    raw_data = []
    for row in reader:
        raw_data.append(row)
    csvfile.close()


    #defects_dict = make_defects_dict()







    # словарь по лифтам, внутри словарь по кол-ву включений
    all_stats = defaultdict(lambda: defaultdict(lambda: None))

    # перебираем всё что прочитали
    for x in raw_data:
        # 0, 1, 2 это идентификатор лифта, датавремя вычитывания, кол-во включений
        id_lift = x[0]
        num = int(x[2])
        dt = datetime.strptime(x[1], "%Y-%m-%d %H:%M:%S.%f")  # преобразуем в datetime
        rounded_dt = dt.replace(microsecond=0, second=0, minute=0)  # округлим до часа

        # если ключ новый, присваиваем, если старый - добавляем к старому
        if all_stats[id_lift][rounded_dt] is None:
            all_stats[id_lift][rounded_dt] = num
        else:
            all_stats[id_lift][rounded_dt] += num

    for lift in all_stats:
        norm_num(all_stats[lift])

    # словарь статусов {(лифт, дата) : статус}
    statuses = {}
    i = start_date
    while i < stop_date:
        for lift in all_stats:
            key = i, lift
            statuses[key] = True

        i = i + timedelta(hours=1)

    ddd = make_defect_statuses_dict()
    # print("Словарь за заполнения")
    # for x in sorted(ddd):
    #     print(x, ddd[x], sep=';')
    defects_dict = fill_spaces(ddd, all_stats.keys())
    defects_dict = make_defects_from_statuses(defects_dict)

    # print("Словарь после заполнения")
    # for x in sorted(ddd):
    #     print(x, ddd[x], sep=';')

    #
    # print("==========")


    # delta это период простоя, при котором мы считаем лифт поломатым
    delta = timedelta(hours=t_stat)
    delta_events = timedelta(hours=t_events)
    one_hour = timedelta(hours=1)
    count_statuses = {}  # почасовое количество неисправностей для всех лифтов
    count_daily_statuses = defaultdict(lambda: 0)  # посуточное количество неисправностей для всех лифтов
    i = start_date
    while i < stop_date:  # перебираем дата-время от начала до конца по часам

        sum = 0
        # хотим определить, сколько лифтов неисправно в этот час
        # неисправно = не двигался
        for lift in all_stats:  # для каждой даты-времени перебираем лифты
            j = i + one_hour  # начало периода
            flag = False  # будем считать что лифт по умолчанию не двигается
            while j <= i + delta:  # идем по периоду delta
                if all_stats[lift][j] != 0:  # если наткнулись на лифт с движением
                    flag = True  # значит лифт рабочий
                j += one_hour

            if not flag:  #если лифт всё-таки нерабочий
                defect_flag = False
                j = i - delta_events + one_hour
                # print(j, i - one_hour)
                while j <= i:
                    if defects_dict[j, lift]:  # если дефект найден
                        defect_flag = True
                    j += one_hour

                if defect_flag:
                    print(lift, i, "defect", sep=';')
                    # try:
                    #     print(ddd[i, lift])
                    # except:
                    #     pass
                    statuses[i, lift] = False  # отмечаем это в большом словаре статусов
                    sum += 1  # и увеличиваем счетчик сломанных лифтов в час

        # т.к. в час i мы получаем данные о движении в часе i-1 (то же две строки выше)
        # то статус надо менять не для текущего часа, а для часа минус один
        prev = i.replace(second=0, minute=0)  # округления для одинаковых ключей

        # теперь в sum количество сломанных лифтов за час
        count_statuses[prev] = sum
        count_daily_statuses[prev.replace(hour=0)] += sum
        i += one_hour

    # fname = str(t_stat) + "_" + str(t_events) + ".csv"
    # with open(fname, "w") as f:
    #     f.write(str(t_stat) + " и " + str(t_events) + "\n")
    #     for x in sorted(count_daily_statuses):
    #         #print(count_daily_statuses[x], sep=';')
    #         f.write(str(count_statuses[x]) + "\n")

    return count_daily_statuses


if __name__ == '__main__':

    res = []

    #res.append(process(1, 1))
    res.append(process(1, 1))
    #res.append(process(2, 2))

    dt = start_date
    while dt < stop_date:
        print(dt, end=";")
        for dict in res:
            print(dict[dt], end=";")
        print()
        dt += timedelta(days=1)





























