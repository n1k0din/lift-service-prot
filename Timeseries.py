from datetime import datetime, timedelta
from collections import OrderedDict

from collections.abc import MutableMapping

#from https://stackoverflow.com/questions/24763464/mutable-dictionary-with-fixed-and-ordered-keys
class Timeseries(MutableMapping):
    def __init__(self, start: datetime, stop: datetime, delta: timedelta, default=None):
        self._d = OrderedDict()
        self.start = start
        self.stop = stop
        self.delta = delta

        i = self.start
        while i < self.stop:
            self._d[i] = default
            i += self.delta

    def __getitem__(self, key):
        return self._d[key]

    def __setitem__(self, key, value):
        if key not in self._d:
            raise KeyError("Must not add new keys")
        self._d[key] = value

    def __delitem__(self, key):
        raise NotImplementedError("Must not remove keys")

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)
