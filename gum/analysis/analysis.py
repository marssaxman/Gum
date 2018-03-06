import numpy as np
import onset, tempo
from time import time


class _logtime:
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


def extract(samples, samplerate, features):
    # Generate audio features and add them to the features dictionary.
    if samples.ndim > 1:
        with _logtime("mixdown to mono"):
            samples = np.mean(samples, axis=1)
    with _logtime("quick tempo estimate"):
        bpm = tempo.estimate(samples, samplerate)
        features['tempo'] = bpm
        print "tempo estimate = %.2f" % bpm
    with _logtime("detect onset events"):
        features['onsets'] = onset.detect(samples, samplerate)
    with _logtime("measure tempo"):
        bpm = tempo.detect(samples, samplerate)
        features['tempo'] = bpm
        print "tempo = %.2f" % bpm


