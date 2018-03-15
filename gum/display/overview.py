
import gobject, threading
from gum.lib.event import Signal
try:
    from fast import condense
except ImportError:
    from slow import condense


class Overview(object):

    def __init__(self, sound):
        self.changed = Signal()
        self._sound = sound
        self._start = 0
        self._width = 0
        self._density = 0
        self._values = None
        self._ready = threading.Event()
        self._ready.set()

    def _condense(self, start, width, density):
        if self._sound.ndim == 1:
            data = [self._sound]
        else:
            data = self._sound.transpose()
        o = []
        for channel in data:
            values = condense(channel, start, width, density)
            o.append(values)
        return o

    def set(self, *args):
        self._ready.wait()
        self._ready.clear()
        thread = threading.Thread(target=lambda: self._update(*args))
        thread.daemon = True
        thread.start()

    def _update(self, start, width, density):
        if self._values is None:
            # We have no cached data.
            self._recompute(start, width, density)
            return

        if self._density != density:
            # Zoom level has changed. Old data is unusable.
            self._recompute(start, width, density)
            return

        start = int(start)
        stop = start + width
        old_stop = self._start + self._width
        inter_start = max(start, self._start)
        inter_stop = min(stop, old_stop)

        if stop <= self._start or start >= old_stop:
            # None of the cached data applies to the requested interval.
            self._recompute(start, width, density)
            return

        # Some of the data in the cache is relevant. Compute the missing part.
        head, tail = [], []
        if start < inter_start:
            head = self._condense(start, inter_start - start, density)
        if inter_stop < stop:
            tail = self._condense(inter_stop, stop - inter_stop, density)

        i, j = [int(x - self._start) for x in (inter_start, inter_stop)]
        body = zip(*self._values)[i:j]
        ov = zip(*head) + body + zip(*tail)
        ov = zip(*ov)
        ov = [list(t) for t in ov]
        self._finish_update(start, width, density, ov)

    def _recompute(self, start, width, density):
        values = self._condense(start, width, density)
        self._finish_update(start, width, density, values)

    def _finish_update(self, start, width, density, values):
        self._start = start
        self._width = width
        self._density = density
        self._values = values
        self._ready.set()
        gobject.idle_add(lambda x: x.changed(), self)

    def get(self):
        self._ready.wait()
        return self._values



DTYPE = 'float64'


def test_overview():
    import numpy
    l = 1000000
    b = numpy.array(range(l), DTYPE)
    assert len(display.condense(b, 0, l, l/10)) == 10
    assert len(display.condense(b, 0, l, l/100)) == 100


def test_Overview():
    import numpy

    cache = Overview(numpy.array([1, 2, 3, 4], DTYPE))
    o = cache.get(start=0, width=4, density=1)
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]

    o2 = cache.get(start=0, width=4, density=1)
    assert o2 == o
    assert o2 is o

    cache = Overview(numpy.array([1, 2, 3, 4], DTYPE))
    o3 = cache.get(start=0, width=4, density=1)
    assert o3 == o
    assert o3 is not o

    cache = Overview(numpy.array(range(1000), DTYPE))
    o1 = cache.get(start=0, width=10, density=10)
    o2 = cache.get(start=4, width=10, density=10)
    o3 = cache.get(start=0, width=10, density=10)
    o4 = cache.get(start=4, width=10, density=10)
    assert o1 == o3
    assert o2 == o4
    assert o1[0][4:] == o2[0][:6], str(o1[0][4:]) + str(o2[0][:6])


if __name__ == "__main__":
    test_overview()
    test_OverviewCache()
