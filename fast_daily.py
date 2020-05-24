import csv
from collections import defaultdict, namedtuple

FIRST_HOUR = '00'
LAST_HOUR = '23'

daylift = namedtuple('daylift', ['day', 'lift'])


def write_dict(d: dict, filename='daily_sum.csv'):
    with open(filename, 'w') as f:
        for k in d:
            f.write("{};{}\n".format(k, d[k]))


# на случай если мы захотим увидеть не сумму, а список дат, когда не ездил лифт
def write_date_lift_wo_moving(d: dict, filename='daily.csv'):
    with open(filename, 'w') as f:
        for k in d:
            try:
                if d[k][FIRST_HOUR] == d[k][LAST_HOUR]:
                    f.write("{};{}\n".format(k.day, k.lift))
            except KeyError:
                pass



# data - {daylift : {FIRST_HOUR | LAST_HOUR : num}}
def filtered(data):
    for daylift, subdict in data.items():
        if subdict.get(FIRST_HOUR) and subdict.get(LAST_HOUR) and subdict[FIRST_HOUR] == subdict[LAST_HOUR]:
            yield daylift


def sum_lifts_wo_moving(d):
    daily_sum = defaultdict(int)
    for daylift in filtered(d):
        daily_sum[daylift.day] += 1

    return daily_sum


def main():

    filename = 'statdriv.csv'
    csv.register_dialect('win', delimiter=';')

    d = defaultdict(dict)
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, dialect='win')
        _ = reader.__next__()  # проигнорируем первую строку с заголовком

        for lift, dt, num in reader:
            # 19.11.2019 00:00:00.000
            day = dt[:10]
            hour = dt[11:13]

            key = daylift(day, lift)
            # нас интересует первое появление 00 часов и последнее появление 23 часов
            if (hour == FIRST_HOUR and key not in d) or hour == LAST_HOUR:
                d[key][hour] = num

    daily = sum_lifts_wo_moving(d)
    write_dict(daily)
    write_date_lift_wo_moving(d)


if __name__ == '__main__':
    main()
