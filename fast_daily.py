import csv
from collections import defaultdict

FIRST_HOUR = '00'
LAST_HOUR = '23'


def sum_lifts_wo_moving(d: dict):
    daily_sum = defaultdict(int)

    for k in d:
        try:
            if d[k][FIRST_HOUR] == d[k][LAST_HOUR]:
                daily_sum[k[0]] += 1
        except KeyError:
            pass

    return daily_sum


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
                    f.write("{};{}\n".format(k[0], k[1]))
            except KeyError:
                pass


def main():
    filename = 'statdriv.csv'
    csv.register_dialect('win', delimiter=';')

    d = defaultdict(dict)
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, dialect='win')
        _ = reader.__next__()

        for lift, dt, num in reader:
            # 19.11.2019 00:00:00.000
            day = dt[:10]
            hour = dt[11:13]

            key = day, lift
            if (hour == FIRST_HOUR and key not in d) or hour == LAST_HOUR:
                d[key][hour] = num

    daily = sum_lifts_wo_moving(d)
    write_dict(daily)


if __name__ == '__main__':
    main()
