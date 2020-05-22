import csv
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta

daylift = namedtuple('daylift', ['day', 'lift'])
numi = namedtuple('numi', ['num', 'i'])

#lst = [2, 3, 3, 3, 3, 3, 3, 5, 8, 12, 17, 21, 22, 22, None, 22, 22, 23, 25, 26, 26, 26, 26, 26, 26]
#  мы хотим выяснить, двигался ли лифт в час 0, 1, 2, ... 23
#  т.е. с 0:00 до 1:00, с 1:00 до 2:00 и т.д.
#  запись о абс. включении ГП в час X содержится в статистике в поле X + 1
#      0  1  2  3  4  5  6  7  8  9   10  11  12  13  14    15    16  17  18  19  20  21  22  23  0
test_lst = [2, 3, 3, 3, 3, 3, 3, 5, 8, 12, 17, 21, 22, 22, None, None, 23, 23, 25, 26, 26, 26, 26, 26, 26]

def truly(d):
    for key, value in d.items():
        if value:
            yield key, value

def falsy(d):
    for key, value in d.items():
        if not value:
            yield key, value



def foo(lst):
    d = {}
    last_truly = None
    for i in range(1, 24 + 1):
        k = i - 1
        if lst[i] is None:  # если запись пропущена, прямо сейчас мы сказать ничего не сможем
            d[k] = None  # и значит статус в час i - 1 = Без статуса
            print(k, "None потому что пропущена i запись *DEBUG*")
            if lst[i - 1]:
                last_truly = numi(lst[i - 1], i - 1)
                print(last_truly, "*DEBUG*")
        else:

            if lst[i - 1] is None:  # если текущая не пропущена, а предыдущая пропущена
                d[k] = None
                print(k, "None потому что пропущена (i-1) запись *DEBUG*")
                if lst[i] == last_truly.num:
                    j = i - 1
                    while d.get(j, -1) is None:
                        d[j] = False
                        print(j, "None заменено на False *DEBUG*")
                        j -= 1
            else:
                d[k] = False if lst[i] == lst[i - 1] else True

    return d










def main():
    filename = 'statdriv.csv'
    csv.register_dialect('win', delimiter=';')

    d = defaultdict(dict)
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, dialect='win')
        _ = reader.__next__()  # проигнорируем первую строку с заголовком

        for lift, dt, num in reader:
            # 19.11.2019 00:00:00.000
            dt = dt[:13]
            dt = datetime.strptime(dt, "%Y-%m-%d %H")
            # dt = dt - timedelta(hours=1)
            key = daylift(dt, lift)
            if key not in d:  # нас интересуют только первые записи
                d[key] = num


    for x in d:
        print(x, d[x])




if __name__ == '__main__':
    main()
    rd = foo(test_lst)
    for date, state in falsy(rd):
        print(date, state)