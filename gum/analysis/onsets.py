import numpy as np


def _windows(source, window_size, step_size):
    # Yield a sequence of views onto the source, which must be normalized mono.
    # We'll pad the beginning by half a window so that time zero happens at
    # index zero, and we'll pad the end by whatever we need to line things up.
    for i in range(0, len(source), step_size):
        start = i - (window_size / 2)
        stop = start + window_size
        frame = None
        if start < 0:
            frame = np.zeros(window_size)
            frame[-start:] = source[0:stop]
        elif stop > len(source):
            frame = np.zeros(window_size)
            frame[:len(source)-stop] = source[start:]
        else:
            frame = source[start:stop]
        yield frame


def _moving_average(array, num_past, num_ahead):
    avg = np.empty_like(array)
    # Preload the sum as though we had just processed the previous frame.
    sum = array[:num_ahead - 1].mean()
    maxindex = len(array)
    width = num_past + num_ahead
    for i in range(maxindex):
        sum += array[i + num_ahead] if maxindex-i > num_ahead else 0
        sum -= array[i - num_past] if i >= num_past else 0
        avg[i] = sum / width
    return avg


def _moving_maximum(array, num_past, num_ahead):
    maxes = np.empty_like(array)
    maxindex = len(array)
    for i in range(maxindex):
        start = max(i - num_past, 0)
        stop = min(i + num_ahead, maxindex)
        maxes[i] = array[start:stop].max()
    return maxes


def _detect(samples, samplerate):
    """
    Find onset points by measuring spectral flux and looking for peaks.
    Returns an array of sample index numbers.
    """
    # Slice the signal into windows. The FFT window size must be a power of 2.
    # The lowest frequency we can measure equals samplerate/window_size.
    # At 44100 Hz, this will be 21.53 Hz.
    window_size = 2048
    # The step size determines our timing resolution. This is a tradeoff with
    # processing time. Human perception tends to lump any onsets within 50 ms
    # into a single event, so we'll keep our step size below half that. This
    # number does not need to be a power of 2, but it feels convenient.
    step_size = 256
    windows = _windows(samples, window_size, step_size)

    # Get a magnitude spectrogram by taking the absolute value of the FFT.
    # The rfft variant truncates the symmetric terms for us.
    # Use a hamming function to taper off the overlap between windows.
    mask = np.hamming(window_size)
    spectrogram = (np.abs(np.fft.rfft(f * mask)) for f in windows)

    # Compute the spectral flux. Flux frames occur between spectral frames, so
    # the start time of flux frame 0 happens at sample number (step_size/2).
    def _spectral_flux():
        prev = next(spectrogram)
        for cur in spectrogram:
            yield np.maximum(cur - prev, 0)

    # Compute the onset envelope by aggregating flux across the frequency range.
    onset = np.fromiter((np.sum(f) for f in _spectral_flux()), np.float)

    # Compute a rolling average and maximum. The parameters to each function
    # express the number of past and future frames to include in the window.
    # The size of the maximum window, in particular, has a strong effect on the
    # selection of peaks.
    average = _moving_average(onset, 12, 12)
    maximum = _moving_maximum(onset, 2, 6)

    # Events occur at points where the signal is both equal to the local max
    # and greater than the local average by some empirically-chosen threshold
    # factor. 
    threshold = average * 1.5
    detection = onset * (onset == maximum) * (onset >= threshold)

    # Find the frames which still have nonzero values, get their indexes, and
    # convert flux-frame indexes back to sample indexes.
    return np.nonzero(detection)[0] * step_size + step_size/2

    # Future: backtrack each onset to the zero-crossing nearest the local
    # energy minimum preceding the spectral flux peak.


def detect(sound):
    samples = sound.frames
    if samples.ndim > 1:
        samples = np.mean(samples, axis=1)
    return _detect(samples, sound.samplerate)

