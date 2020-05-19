import csv
from collections import defaultdict


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

            if hour == '00':
                if key not in d:
                    d[key]['start'] = num
            elif hour == '23':
                d[key]['stop'] = num


    daily = defaultdict(int)
    for x in d:
        try:
            if d[x]['stop'] == d[x]['start']:
                daily[x[0]] += 1
        except:
            pass

    with open('new_daily_sum.csv', 'w') as f:

        for x in daily:
            f.write("{};{}\n".format(x, daily[x]))




    # with open('new_daily.csv', 'w') as f:
    #     for x in d:
    #         try:
    #             if d[x]['stop'] == d[x]['start']:
    #                 f.write("{};{}\n".format(x[0], x[1]))
    #         except:
    #             pass


if __name__ == '__main__':
    main()