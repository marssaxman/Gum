import numpy as np
import onset, tempo, beat
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
    with _logtime("measure onset envelope"):
        onset_strength, onset_fps = onset.strength(samples, samplerate)
    with _logtime("detect onset events"):
        features['onsets'] = onset.events(onset_strength, onset_fps)
    with _logtime("measure tempo"):
        new_bpm = tempo.detect(samples, samplerate)
        bpm_diff = bpm - new_bpm
        bpm = new_bpm
        features['tempo'] = bpm
        print "tempo = %.2f (estimate was off by %.2f)" % (bpm, bpm_diff)
    with _logtime("track beats"):
        features['beats'] = beat.track_onset(onset_strength, onset_fps, bpm)

