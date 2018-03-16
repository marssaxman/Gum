
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
        thread = threading.Thread(target=self._update, args=args)
        thread.daemon = True
        thread.start()

    def _update(self, start, width, density):
        start = int(start)
        width = int(width)
        stop = start + width
        self_stop = self._start + self._width

        if self._values is None:
            values = self._condense(start, width, density)
        elif self._density > density:
            values = self._zoom_in(start, width, density)
        elif self._density < density:
            values = self._zoom_out(start, width, density)
        elif start < self._start and stop > self._start:
            values = self._scroll_left(start, width, density)
        elif stop > self_stop and start < self_stop:
            values = self._scroll_right(start, width, density)
        else:
            values = self._condense(start, width, density)
        self._start = start
        self._width = width
        self._density = density
        self._values = values
        self._ready.set()
        gobject.idle_add(lambda x: x.changed(), self)

    def _scroll_left(self, start, width, density):
        assert start < self._start and width == self._width
        stop = start + width
        assert stop > self._start
        ov = self._condense(start, self._start - start, density)
        keep_width = stop - self._start
        for i, channel in enumerate(self._values):
            ov[i] = ov[i] + channel[:keep_width]
        return ov

    def _scroll_right(self, start, width, density):
        assert width == self._width
        self_stop = self._start + self._width
        assert start < self_stop
        stop = start + width
        ov = self._condense(self_stop, stop - self_stop, density)
        keep_start = start - self._start
        for i, channel in enumerate(self._values):
            ov[i] = channel[keep_start:] + ov[i]
        return ov

    def _zoom_in(self, start, width, density):
        return self._condense(start, width, density)

    def _zoom_out(self, start, width, density):
        return self._condense(start, width, density)

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
