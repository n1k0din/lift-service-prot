import csv
from datetime import datetime, timedelta
from collections import defaultdict


def main():
    filename = 'statdriv.csv'
    csv.register_dialect('win', delimiter=';')
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    d = defaultdict(dict)
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, dialect='win')
        _ = reader.__next__()

        for lift, dt, num in reader:

            day, time = dt[:len(dt) - 4].split()
            hour = time.split(':')[0]

            key = day, lift

            if hour == '00':
                if key not in d:
                    d[key]['start'] = num
            elif hour == '23':
                d[key]['stop'] = num

    with open('new_daily.csv', 'w') as f:
        for x in d:
            try:
                if d[x]['stop'] == d[x]['start']:
                    f.write("{};{}\n".format(x[0], x[1]))
            except:
                pass








if __name__ == '__main__':
    main()