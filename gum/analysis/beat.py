import numpy as np


def track_onset(envelope, framerate, bpm):
    # Given an estimated overall tempo, search the envelope for an arrangement
    # of onset peaks which produces the best fit for a beat grid. This is from
    # the paper "Beat Tracking with Dynamic Programming" by Daniel P. W. Ellis.
    # We will return an array of estimated beat times, in seconds.
    assert bpm > 0
    assert framerate > 0
    period = round(60.0 * framerate / bpm)

    # Make sure the onset envelope is sane: it should have enough length that
    # it is plausible we might find beats in it, and it should range 0..1.
    if len(envelope) < framerate:
        return np.zeros(0, dtype=np.float)
    onset_norm = envelope.std(ddof=1)
    if onset_norm > 0:
        envelope /= onset_norm

    # Reduce local fluctuations, smoothing the envelope with a Gaussian window
    # spanning 1/32 of the estimated beat interval.
    window = np.exp(-0.5 * (np.arange(-period, period+1)*32.0/period)**2)
    #window = np.exp(-0.5 * np.linspace(-32.0, 32.0, period*2+1) ** 2)
    localscore = np.convolve(envelope, window, 'same')

    # Use a log-gaussian cost function for distance from expected bpm.
    tightness = 100
    window = np.arange(-2 * period, -np.round(period / 2) + 1, dtype=np.int)
    txwt = -tightness * (np.log(-window / period) ** 2)
    # Are we on the first beat?
    #!!! the Ellis paper starts with backlinks at -1, not 0?
    backlink = np.zeros_like(localscore, dtype=np.int)
    cumscore = np.zeros_like(localscore)
    first_beat = True
    for i, score in enumerate(localscore):
        # Are we reaching back before time 0?
        z_pad = np.maximum(0, min(-window[0], len(window)))
        # Search over all possible predecessors
        candidates = txwt.copy()
        candidates[z_pad:] = candidates[z_pad:] + cumscore[window[z_pad:]]
        # Find the best preceding beat
        beat_location = np.argmax(candidates)
        # Add the local score
        cumscore[i] = score + candidates[beat_location]
        # Special case the first onset.  Stop if the local score is small
        if first_beat and score < 0.01 * localscore.max():
            backlink[i] = -1
        else:
            backlink[i] = window[beat_location]
            first_beat = False
        # Update the time range
        window = window + 1

    # Get the position of the last beat. Measure the degree to which each
    # frame is a local maximum, then pick local maxima which exceed the global
    # median by a factor of 2, then select the last of these.
    score_pad = np.pad(cumscore, [(1,1)], mode='edge')
    maxes = (cumscore > score_pad[:-2]) & (cumscore >= score_pad[2:])
    med_score = np.median(cumscore[np.argwhere(maxes)])
    last_beat = np.argwhere((cumscore * maxes * 2 > med_score)).max()

    # Reconstruct the most probable beat path from the series of backlinks,
    # then create an array in ascending order.
    beats = [last_beat]
    while backlink[beats[-1]] >= 0:
        beats.append(backlink[beats[-1]])
    beats = np.array(beats[::-1], dtype=np.int)

    # Discard low-probability beats at the beginning and end.
    smooth_boe = np.convolve(localscore[beats], np.hanning(5), 'same')
    threshold = 0.5 * ((smooth_boe ** 2).mean() ** 0.5)
    valid = np.argwhere(smooth_boe > threshold)
    beats = beats[valid.min():valid.max()]

    # Convert the beat frame indexes into timestamps.
    return (beats.astype(np.float) - 1) / framerate

