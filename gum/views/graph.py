# Gum sound editor (https://github.com/stackp/Gum)
# Copyright 2009 (C) Pierre Duquesne <stackp@online.fr>
# Licensed under the Revised BSD License.

from gum.lib.event import Signal
from display import Display

class Graph(object):
    """Scale the sound visualization.

    When audio is drawn on the screen, several frames are condensed in
    one column of pixels. This object computes what to display,
    according to zooming and position in the sound.

    """

    def __init__(self, sound):
        self.changed = Signal()
        self._sound = None
        self._display = None
        self._view_start = 0
        self._width_px = 100.
        self._density = 1.
        self.set_sound(sound)

    def _get_density(self):
        return self._density

    def _set_density(self, value):
        mini = 1
        maxi = max(mini, self.numframes() / float(self._width_px))
        self._density = self._gauge(value, mini, maxi)

    density = property(_get_density, _set_density)

    def _frame2cell(self, frame):
        return frame / float(self._density)

    def _cell2frame(self, cell):
        return cell * self._density

    def set_sound(self, sound):
        self._sound = sound
        self._view_start = 0  # is a cell
        self.density = self.numframes() / float(self._width_px)
        self._sound.changed.connect(self.on_sound_changed)
        self.on_sound_changed()

    def on_sound_changed(self):
        self._display = Display(self._sound.frames)
        self._update()

    def set_width(self, width):
        start, end = self.view()
        self._width_px = width
        self.density = (end - start) / float(width)
        self.move_to(start)

    def _update(self):
        # Clamp the view parameters within reasonable limits.
        numcells = self._frame2cell(self.numframes())
        if self._view_start + self._width_px > numcells:
            self._view_start = numcells - self._width_px
        if self._view_start < 0:
            self._view_start = 0
        # Move the overview to the new display region.
        self._display.set(self._view_start, self._width_px, self._density)
        self.changed()

    def numframes(self):
        return len(self._sound.frames)

    def view(self):
        """
        Return start and end frames; end is exclusive.
        """
        start = self._cell2frame(self._view_start)
        end = start + self._cell2frame(self._width_px)
        n = self.numframes()
        if end > n:
            end = n
        return (start, end)

    def set_view(self, start, end):
        self.density = (end - start) / float(self._width_px)
        self.move_to(start)

    def move_to(self, frame):
        "Moves the view start and keep the view length"
        self._view_start = self._frame2cell(frame)
        self._update()

    def center_on(self, frame):
        self.move_to(frame - (self._width_px - 1) * self.density * 0.5)

    def frmtopxl(self, f):
        "Converts a frame index to a pixel index."
        return int(self._frame2cell(f) - self._view_start)

    def pxltofrm(self, p):
        "Converts a pixel index to a frame index."
        f = self._cell2frame(self._view_start + p)
        return int(round(self._gauge(f, 0, self.numframes())))

    def _gauge(self, value, mini, maxi):
        "Calibrate value between mini and maxi."
        if value < mini:
            value = mini
        if value > maxi:
            value = maxi
        return value

    def _zoom(self, factor):
        """Expand or shrink view according to factor.

        0 < factor < 1     zoom in
            factor = 1     unchanged
        1 < factor < +Inf  zoom out

        The zoom factor is relative to the current zoom, ie.::

            self._zoom(x, n)
            self._zoom(x, m)

        is equivalent to::

            self._zoom(x, n * m)

        """
        self.density *= factor

    def middle(self):
        start, end = self.view()
        return start + (end - 1 - start) * 0.5

    def zoom_in(self):
        "Make view twice smaller, centering on the middle of the view."
        mid = self.middle()
        self._zoom(0.5)
        self.center_on(mid)

    def zoom_out(self):
        "Make view twice larger, centering on the middle of the view."
        mid = self.middle()
        self._zoom(2)
        self.center_on(mid)

    def zoom_out_full(self):
        "Fit everything in the view."
        self.set_view(0, self.numframes())

    def is_zoomed_out_full(self):
        start, end = self.view()
        return start == 0 and end == self.numframes()

    def zoom_on(self, pixel, factor):
        point = self.pxltofrm(pixel)
        self._zoom(factor)
        self.move_to(point - pixel * self.density)

    def zoom_in_on(self, pixel):
        self.zoom_on(pixel, 0.8)

    def zoom_out_on(self, pixel):
        self.zoom_on(pixel, 1.2)

    def _scroll(self, factor):
        """Shift the view.

        A negative factor shifts the view to the left, a positive one
        to the right. The absolute value of the factor determines the
        length of the shift, relative to the view length. For example:
        0.1 is 10%, 0.5 is one half, 1.0 is 100%.

        """
        l = self._width_px * factor
        self._view_start += l
        self._update()

    def scroll_left(self):
        self._scroll(-0.1)

    def scroll_right(self):
        self._scroll(0.1)

    def draw(self, context, width, height):
        return self._display.draw(context, width, height)

# Test functions


DTYPE = 'float64'


def test_middle():
    from gum.lib.mock import Mock, Fake
    import numpy
    sound = Mock({"numchan": 1})
    sound.changed = Fake()
    sound.frames = []
    g = Graph(sound)
    for nframes, mid in [(4, 1.5), (9, 4), (10, 4.5)]:
        sound.frames = numpy.array(range(nframes))
        g.set_sound(sound)
        assert g.middle() == mid


def test_Graph():
    from gum.lib.mock import Mock, Fake
    import numpy

    sound = Mock({"numchan": 1})
    sound.changed = Fake()
    sound.frames = numpy.array(range(1000), DTYPE)

    c = Graph(sound)
    c.set_width(200)
    o = c.channels()

    class Foo:
        def foo(self):
            print "Changed."
    f = Foo()
    c = Graph(sound)
    c.changed.connect(f.foo)
    c.set_width(200)
    o = c.channels()

    # stereo
    import numpy
    sound = Mock({"numchan": 2})
    sound.changed = Fake()
    data = numpy.array([[1, 1], [2, 2], [3, 3]], DTYPE)
    sound.frames = data
    c = Graph(sound)
    o = c.channels()
    assert(len(o)) == 2


def test_zoom():
    from gum.lib.mock import Mock, Fake
    import numpy

    sound = Mock({"numchan": 1})
    data = numpy.array([1, 2, 3, 4], DTYPE)
    sound.frames = data
    sound.changed = Fake()

    g = Graph(sound)

    g.set_width(4)
    g._zoom(1)
    g.center_on(1.5)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]

    g._zoom(factor=1)
    g.center_on(0)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]

    g._zoom(1)
    g.center_on(6)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]

    g._zoom(factor=0.5)
    g.center_on(1.5)
    g.set_width(4)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]

    g.set_width(2)
    g._zoom(0.5)
    g.center_on(0)
    o = g.channels()
    assert o == [[(1, 1), (2, 2)]]

    g.set_width(4)
    g._zoom(0.25)
    g.center_on(0)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]

    g.set_width(4)
    g._zoom(4)
    g.center_on(4)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]], o

    g.set_width(100)
    data = numpy.array(range(3241))
    sound.frames = data
    g.zoom_out_full()
    g._zoom(factor=0.5)
    g._zoom(factor=0.5)
    start, end = g.view()
    g.zoom_out_full()
    g._zoom(factor=0.5 * 0.5)
    assert (start, end) == g.view()


def test_zoom_in():
    import numpy
    from gum.lib.mock import Mock, Fake
    sound = Mock({"numchan": 1})
    sound.changed = Fake()

    data = numpy.array([1, 2, 3, 4], DTYPE)
    sound.frames = data
    g = Graph(sound)

    g.set_width(2)
    g.zoom_in()
    o = g.channels()
    assert o == [[(2, 2), (3, 3)]]

    g.zoom_out()
    g.set_width(4)
    o = g.channels()
    assert o == [[(1, 1), (2, 2), (3, 3), (4, 4)]]


def test_zoom_in_on():
    import numpy
    from gum.lib.mock import Mock, Fake
    sound = Mock({"numchan": 1})
    sound.changed = Fake()
    data = numpy.array([1, 2, 3, 4], DTYPE)
    sound.frames = data
    g = Graph(sound)
    g.set_width(2)

    g.zoom_in_on(0)
    assert g.channels() == [[(1, 2), (3, 3)]]

    g.zoom_out()
    g.zoom_in_on(1)
    assert g.channels() == [[(1, 2), (3, 3)]]

    g.zoom_out()
    g.zoom_in_on(2)
    assert g.channels() == [[(1, 2), (3, 3)]]


def test_scroll():
    import numpy
    from gum.lib.mock import Mock, Fake

    sound = Mock({})
    data = numpy.array([1, 2, 3, 4])
    sound.frames = data
    sound.changed = Fake()

    g = Graph(sound)
    g.set_width(4)

    g.scroll_right()
    length = g.numframes()
    start, end = g.view()
    assert length == 4
    assert start == 0
    assert end == 4


def test_density():
    from gum.models import Sound
    import gum
    g = Graph(Sound(gum.basedir + "/data/test/test1.wav"))
    g.set_width(700)
    g.zoom_in()
    g.channels()
    g.zoom_in()
    g.channels()
    g.zoom_in()
    d = g.density

    pos = [26744.9875, 18793.775, 15902.425, 13011.075, 10119.725, 7228.375,
           4337.025, 1445.675, 0.0, 2891.35, 5782.7, 8674.05, 11565.4,
           14456.75, 17348.1, 20239.45]

    for x in pos:
        g.move_to(x)
        assert d == g.density


def test_channels():
    import numpy
    from gum.lib.mock import Mock, Fake
    sound = Mock({"numchan": 1})
    sound.changed = Fake()
    sound.frames = numpy.array(range(1000000), DTYPE)
    g = Graph(sound)

    for w in [1, 10, 11, 12, 13, 14, 15, 29, 54, 12.0, 347, 231., 1030]:
        g.set_width(w)
        c = g.channels()
        assert len(c[0]) == w, \
            "expected: %d, got: %d, density: %f, last value: %s " % \
            (w, len(c[0]), g.density, str(c[0][-1]))


if __name__ == "__main__":
    test_middle()
    test_Graph()
    test_zoom()
    test_zoom_in()
    test_zoom_in_on()
    test_density()
    test_scroll()
    test_channels()
