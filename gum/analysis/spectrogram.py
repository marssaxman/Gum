import numpy as np


def _frames(source, size, step):
    if len(source) <= 0:
        return
    # Yield a sequence of views onto the source. We assume that the window
    # size is an even multiple of the step size.
    # The first frame will be centered on index zero. We will pad to the left
    # with zeros until the left edge of the window reaches the sample data.
    for stop in range(size / 2, size, step):
        frame = np.zeros(size)
        frame[size - stop:] = source[:stop]
        yield frame
    # Most frames will simply be non-copied views on the source array.
    for start in range(0, len(source)-size, step):
        stop = start + size
        yield source[start:stop]
    # Trailing frames will be padded to the right with zeros, until the
    # center of the frame has reached or passed the end of the array.
    remaining = size - step + (len(source) % step)
    for offset in range(-remaining, -size / 2, step):
        frame = np.zeros(size)
        frame[:-offset] = source[offset:]
        yield frame


class STFT(object):

    def __init__(self,
            signal=None,
            size=1024,
            step=None,
            func=np.fft.fft,
            window=np.hanning):
        self.signal = signal
        self.size = size
        self.step = step
        self.func = func
        self.window = window

    def __len__(self):
        assert not self.signal is None
        return int(np.floor(len(self.signal) / self.size))

    def __iter__(self):
        assert not self.signal is None
        mask = self.window(self.size)
        frames = _frames(self.signal, self.size, self.step)
        return (self.func(f * mask) for f in frames)

    def __call__(self, *args, **kwargs):
        attrs = dict(self.__dict__.iteritems())
        attrs.update(kwargs)
        return STFT(*args, **attrs)

    def astype(self, *args, **kwargs):
        return np.array(self, *args, **kwargs)

    @property
    def ndim(self):
        if self.signal:
            if hasattr(self.signal, 'ndim'):
                return self.signal.ndim + 1
            else:
                return 1
        else:
            return 0

    def magnitude(self):
        return self(func=np.abs)

    def power(self):
        return self(func=np.square)

    def phase(self):
        return self(func=np.angle)


def stft(*args, **kwargs): return STFT(*args, **kwargs)
def magnitude(*args, **kwargs): return STFT(*args, **kwargs).magnitude()
def power(*args, **kwargs): return STFT(*args, **kwargs).power()
def phase(*args, **kwargs): return STFT(*args, **kwargs).phase()

