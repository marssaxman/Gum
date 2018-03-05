import numpy as np
import onsets, tempo
import threading
from time import time
import gobject


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


def _update(sound, name, value):
    def notify(args):
        sound, name, value = args
        sound.features[name] = value
        sound.changed()
    gobject.idle_add(notify, (sound, name, value))


def _analyze(sound):
    # This function runs inside a thread. We generate audio features and add
    # them to the target sound object's 'features' dictionary. Whenever we have
    # more data, we notify the sound object so it can update itself.
    samples = sound.frames
    if samples.ndim > 1:
        with _logtime("mixdown to mono"):
            samples = np.mean(samples, axis=1)
    with _logtime("quick tempo estimate"):
        bpm = tempo.estimate(samples, sound.samplerate)
        _update(sound, 'tempo', bpm)
        print "tempo estimate = %.2f" % bpm
    with _logtime("detect onset events"):
        _update(sound, 'onsets', onsets.detect(samples, sound.samplerate))
    with _logtime("measure tempo"):
        bpm = tempo.detect(samples, sound.samplerate)
        _update(sound, 'tempo', bpm)
        print "tempo = %.2f" % bpm


def evaluate(sound):
    # Begin evaluating this sound object, asynchronously. We will return a
    # features object that will accumulate audio features as we come up with
    # them. Perhaps the features object will be able to trigger more analysis
    # later, if some client requests a feature we haven't computed yet.
    sound.features = {}
    thread = threading.Thread(target=lambda: _analyze(sound))
    thread.daemon = True
    thread.start()


