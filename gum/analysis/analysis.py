import numpy as np
from samplerate import resample
import onset, tempo, beat
from time import time


class _logtime:
    """Context manager which prints out the elapsed time."""
    indent = ""
    def __init__(self, msg):
        self.msg = msg
    def __enter__(self):
        _logtime.indent += "-"
        print "%s>logtime(%s) enter..." % (_logtime.indent, self.msg)
        self.start = time()
    def __exit__(self, type, value, traceback):
        duration = time() - self.start
        unit = "s"
        if duration < 1.0:
            duration *= 1000.0
            unit = "ms"
        print "<%slogtime(%s) exit: %.2f %s" % (
            _logtime.indent, self.msg, duration, unit
        )
        _logtime.indent = self.indent[:-1]


def _timefunc(f):
    def wrap(*args, **kwargs):
        with _logtime(f.__name__):
            return f(*args, **kwargs)
    return wrap


@_timefunc
def _normalize(signal, rate):
    # Mix to a single channel, since we only care about time intervals
    # which need to be the same regardless of stereo effects.
    if hasattr(signal, 'ndim') and signal.ndim > 1:
        with _logtime("mixdown to mono"):
            signal = signal.mean(axis=1).astype(np.float)
    if rate > 22050:
        # Downsampling 2x saves an amazing amount of time and improves tracking
        # accuracy very substantially. Fixing rate at 22k also lets us make
        # reasonable assumptions about FFT size.
        with _logtime("downsample to 22050 Hz"):
            signal = resample(signal, 22050.0 / rate, 'sinc_fastest')
    return np.asarray(signal, dtype=np.float), 22050


@_timefunc
def extract(samples, samplerate, features):
    # Generate audio features and add them to the features dictionary.
    samples, samplerate = _normalize(samples, samplerate)
    with _logtime("measure onset envelope"):
        onset_strength, onset_fps = onset.strength(samples, samplerate)
    with _logtime("detect onset events"):
        features['onsets'] = onset.events(onset_strength, onset_fps)
    with _logtime("measure tempo"):
        bpm = tempo.detect(samples, samplerate)
        features['tempo'] = bpm
        print "tempo = %.2f bpm" % bpm
    with _logtime("track beats"):
        # Track strongest beat alignments in the onset envelope.
        beats = beat.track_onset(onset_strength, onset_fps, bpm)
        # Adjust precise time points according to local energy peaks.
        beats = beat.align_energy(beats, onset_fps, samples, samplerate)
        features['beats'] = beats
        # Compute the average BPM based on inter-onset intervals. How far off
        # was our autocorrelation-based estimate?
        ioi = beats[1:] - beats[:-1]
        ioi_avg = ioi.mean()
        ioi_bpm = 60.0 / ioi_avg
        bpm_diff = bpm - ioi_bpm
        print "post-tracking BPM: %.2f (estimate was off by %.2f)" % (ioi_bpm, bpm_diff)

