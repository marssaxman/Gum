import numpy as np
import onsets
import tempo
from time import time

def logtime(start, message):
    elapsed = time() - start
    print "%s time: %.2f" % (message, elapsed)


def apply(sound):
    samples = sound.frames
    if samples.ndim > 1:
        start = time()
        samples = np.mean(samples, axis=1)
        logtime(start, "mixdown to mono")
    start = time()
    odf, framerate = onsets.strength(samples, sound.samplerate)
    logtime(start, "measure onset envelope")
    start = time()
    sound._onsets = onsets.events(odf, framerate)
    logtime(start, "detect onset events")
    start = time()
    sound._tempo = tempo.detect(samples, sound.samplerate)
    print "detected tempo: %.2f" % sound._tempo
    logtime(start, "detect tempo")


