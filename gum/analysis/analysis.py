import numpy as np
import onsets
import tempo
from time import time


class logtime:
    """Context manager which prints out the elapsed time."""
    def __init__(self, msg):
        self.msg = msg
    def __enter__(self):
        print "beginning %s..." % self.msg
        self.start = time()
    def __exit__(self, type, value, traceback):
        duration = time() - self.start
        unit = "s"
        if duration < 1.0:
            duration *= 1000.0
            unit = "ms"
        print "...%s duration: %.2f %s" % (self.msg, duration, unit)


def apply(sound):
    samples = sound.frames
    if samples.ndim > 1:
        with logtime("mixdown to mono"):
            samples = np.mean(samples, axis=1)
    with logtime("quick tempo estimate"):
        sound._tempo = tempo.estimate(samples, sound.samplerate)
        print "tempo estimate = %.2f" % sound._tempo
    with logtime("detect onset events"):
        sound._onsets = onsets.detect(samples, sound.samplerate)
    with logtime("measure tempo"):
        sound._tempo = tempo.detect(samples, sound.samplerate)
        print "tempo = %.2f" % sound._tempo


