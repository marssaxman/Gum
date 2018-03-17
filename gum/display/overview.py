from collections import namedtuple

Cell = namedtuple('Cell', 'min max mean std')


def _condense(data, start, width, density):
    """
    Scale the data by the density factor and slice it into cells. Compute
    the statistical properties of each cell. Return a list of cell values.
    """
    res = []
    start = int(start)
    width = int(width)
    dlen = len(data)
    for i in range(start, start + width):
        a = int(round((i - 0.25) * density))
        b = int(round((i + 1.25) * density))
        if a < 0: a = 0
        if a >= dlen: break
        if b > dlen: b = dlen
        d = data[a:b]
        mini = d.min()
        maxi = d.max()
        mean = d.mean() if dlen >= 2 else mini
        std = d.std() if dlen > 2 else 0
        res.append(Cell(mini, maxi, mean, std))
    return res


def _merge_cells(vals):
    o_min, o_max, o_mean, o_std = 1, -1, 0, 0
    for v in vals:
        o_min = min(v.min, o_min)
        o_max = max(v.max, o_max)
        o_mean += v.mean
        o_std += v.std
    o_mean /= len(vals)
    o_std /= len(vals)
    return Cell(o_min, o_max, o_mean, o_std)


class Condense(object):

    def __init__(self, sound):
        self._sound = sound

    def __len__(self):
        return len(self._sound)

    def __call__(self, *args):
        return [_condense(ch, *args) for ch in self._sound.transpose()]


class Downsample(object):

    def __init__(self, source, threshold_density=2048):
        self._source = source
        self._threshold = threshold_density
        self._density = 0.5 * threshold_density
        width = int(float(len(source)) / self._density)
        self._values = source(0, width, self._density)

    def __len__(self):
        return len(self._source)

    def __call__(self, start, width, density):
        if density < self._threshold:
            return self._source(start, width, density)
        out = []
        density /= self._density
        for in_channel in self._values:
            out_channel = []
            for out_x in range(0, width):
                in_start = int(round((start + out_x) * density))
                in_stop = int(round((start + out_x + 1) * density))
                in_stop = min(in_stop, len(in_channel))
                out_v = _merge_cells(in_channel[in_start:in_stop])
                out_channel.append(out_v)
            out.append(out_channel)
        return out


class Scroll(object):

    def __init__(self, source):
        self._source = source
        self._start = 0
        self._width = 0
        self._density = 0
        self._values = None

    def __len__(self):
        return len(self._source)

    def _calc(self, start, width):
        return self._source(start, width, self._density)

    def __call__(self, start, width, density):
        values = None
        if self._values is not None and self._density == density:
            stop = start + width
            self_stop = self._start + self._width
            if start == self._start and stop == self_stop:
                values = self._values
            elif start < self._start and stop > self._start:
                values = self._calc(start, self._start - start)
                keep_width = stop - self._start
                for i, channel in enumerate(self._values):
                    values[i] = values[i] + channel[:keep_width]
            elif stop > self_stop and start < self_stop:
                values = self._calc(self_stop, stop - self_stop)
                keep_start = start - self._start
                for i, channel in enumerate(self._values):
                    values[i] = channel[keep_start:] + values[i]
        if not values:
            self._density = density
            values = self._calc(start, width)
        self._start = start
        self._width = width
        self._values = values
        return self._values


def Overview(sound):
    return Scroll(Downsample(Condense(sound)))

