import csv
from collections import defaultdict
from datetime import datetime, timedelta

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
def is_defect(num:int, flag:int):
    # набор событий индикаторов
    num_with_flags = {132, 145, 147, 149, 160, 161, 162, 164, 176, 144, 181}  # нужно учесть флаг для определения начала
    num_wo_flag = {19}  # событие и есть начало
    #if (num in num_wo_flag) or (num in num_with_flags and flag & 2 != 0):
    if (num in num_wo_flag) or (num in num_with_flags):
        return True
    else:
        return False


def process(t_stat=1, t_events=1):

    csvfile = open('StatDriv.csv', 'r')
    csv.register_dialect('win', delimiter=';' )
    reader = csv.reader(csvfile, dialect="win")
    _ = reader.__next__()
    raw_data = []
    for row in reader:
        raw_data.append(row)
    csvfile.close()

    csvfile_events = open('Events.csv', 'r')
    reader = csv.reader(csvfile_events, dialect='win')
    _ = reader.__next__()
    raw_events = []
    for row in reader:
        raw_events.append(row)
    csvfile_events.close()

    # словарь дефектов {(лифт, дата) : True если дефект}
    defects_dict = defaultdict(lambda: False)  # по умолчанию - НЕ дефект, т.е. всё хорошо
    for event in raw_events:
        id_lift = event[0]
        num = int(event[3])
        flag = int(event[2])
        dt = datetime.strptime(event[1], "%Y-%m-%d %H:%M:%S.%f")  # преобразуем в datetime
        # там ещё текстовое описание в event[4], но мы его проигнорируем
        rounded_dt = dt.replace(second=0, minute=0)  # округлим до часа
        df = is_defect(num, flag)
        if df:  # если событие ошибочное
            if not defects_dict[rounded_dt, id_lift]: #если в словаре False
                defects_dict[rounded_dt, id_lift] = True
            # иначе в словаре True, значит для этого лифта в этот час уже зафиксирована неисправность
            # так тому и быть
    # в результате имеем словарь и по дате-времени и ид лифта можем сказать -
    # была ли зафиксирована неисправность в этот момент

    # словарь по лифтам, внутри словарь по кол-ву включений
    all_stats = defaultdict(lambda: defaultdict(lambda: None))

    start_date = datetime(2020, 2, 1)
    stop_date = datetime(2020, 3, 1)

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
                    # print(lift, i, "defect")
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

    res.append(process(1, 1))
    res.append(process(1, 5))

    start_date = datetime(2020, 2, 1)
    stop_date = datetime(2020, 3, 1)

    dt = start_date
    while dt < stop_date:
        print(dt, end=";")
        for dict in res:
            print(dict[dt], end=";")
        print()
        dt += timedelta(days=1)





























