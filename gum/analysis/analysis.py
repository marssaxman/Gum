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
    if samplerate > 22050:
        # Downsampling 2x saves an amazing amount of time and improves tracking
        # accuracy very substantially
        with _logtime("downsample to 22050 Hz"):
            nu = np.empty(int(len(samples) / 2), dtype=np.float)
            if len(samples) % 2:
                nu[:] = samples[:-1:2] * 0.5
                nu[:] = samples[1::2] * 0.25
                nu[1:] = samples[:-3:2] * 0.25
            else:
                nu[:] = samples[::2] * 0.5
                nu[:] = samples[1::2] * 0.25
                nu[1:] = samples[:-2:2] * 0.25
            samples = nu
            samplerate = int(samplerate / 2)
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

