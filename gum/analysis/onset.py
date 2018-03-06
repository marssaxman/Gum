"""
Onset detection: the first step in musical structure discovery.

We are looking for the attack portions of the various events occuring in some
piece of music. This will be useful for note segmentation, but it is also the
first step in discovering tempo and rhythm pattern structure. At this stage we
want to find all event onsets, regardless of energy level.

We will accomplish this by finding local maxima in the spectral flux, which we
will measure by computing a spectrogram and subtracting the value of each bin
in each frame from the corresponding bin in the preceding frame. Since we are
only interested in attacks, not decays, we will discard negative values. The
overall spectral flux between two frames will be the sum of these positive
differences.

The highest frequency we can analyze is determined by the sampling rate, but
the lowest frequency is determined by the number of samples we supply to the
FFT, which must be a power of 2. The window size also governs the span of time
each spectral frame covers. Longer windows take more CPU time and yield coarser
time resolution, while shorter windows cut off more low-frequency data; what
will our tradeoff be?

Given the likely sampling rate of 44100 Hz, these are our likely choices:
    256 samples -> cutoff 172.27 Hz, interval 5.8 ms
    512 samples -> cutoff 86.13 Hz, interval 11.6 ms
    1024 samples -> cutoff 43.07 Hz, interval 23.2 ms
    2048 samples -> cutoff 21.53 Hz, interval 46.4 ms

While we definitely need some sensitivity to bass, for this application we are
more concerned with timing than frequency composition. It is unlikely that we
will encounter any events which occur only in the 21-43 Hz range, without any
effect on higher frequencies, so we can safely use a 1024-sample FFT window.
"""
WINDOW_SIZE = 1024
"""
Musical tempos run from approximately 60 to 180 BPM, with the median around 120.
Individual notes frequently occur at 16th note intervals - that is, 4x the BPM.
At 120 BPM, with two beats per second, 16th notes are roughly 8 Hz; at 180 BPM
they would be 12 Hz. There are of course musically significant 32nd notes too,
but we can see that the upper limit of note-timing frequency is approximately
20 Hz - which is, not so coincidentally, the lower end of our hearing range.
We can therefore safely assume that each 50 ms interval will contain no more
than one onset.

On the other end of the scale, the minimum resolution for human perception of
time intervals is in the neighborhood 5 ms. This suggests that while our onset
detector need not identify more than one onset in a 2048-sample window, we
must still be able to locate that onset within no more than a 256 sample range.

We can double our timing resolution by overlapping the FFTs, so that the center
of each window sits on the boundary between the adjacent windows. We prevent
samples from being double-counted by weighting their contribution to each FFT
according to distance from the center, using the Hamming function.

With a 1024-sample FFT window, half-steps bring us up to 512-sample resolution,
but we can double it again by computing two parallel streams of FFTs, offset by
256 samples, and interleaving the flux measurements. Once we've gone that far,
though, why not double it again? 128-sample steps yields 3 millisecond timing
precision, which is enough to comfortably distinguish between 120 and 121 BPM.
"""
OVERLAP_FACTOR = 4
STEP_SIZE = WINDOW_SIZE / OVERLAP_FACTOR / 2
"""
After reducing our signal to a series of 128-sample-width flux measurements, we
will identify onsets by looking for local maxima. We will compute a moving
average over 24 frames, or 70 ms, and look for flux values which are more than
one standard deviation higher than the mean. If such a flux peak is also the
maximum value within 8 frames in either direction, we will call it an onset.
"""
import numpy as np


def _windows(source, window_size=WINDOW_SIZE, step_size=STEP_SIZE):
    if len(source) <= 0:
        return
    # Yield a sequence of views onto the source. We assume that the window
    # size is an even multiple of the step size.
    # The first frame will be centered on index zero. We will pad to the left
    # with zeros until the left edge of the window reaches the sample data.
    for stop in range(window_size / 2, window_size, step_size):
        frame = np.zeros(window_size)
        frame[window_size - stop:] = source[:stop]
        yield frame
    # Most frames will simply be non-copied views on the source array.
    for start in range(0, len(source)-window_size, step_size):
        stop = start + window_size
        yield source[start:stop]
    # Trailing frames will be padded to the right with zeros, until the
    # center of the frame has reached or passed the end of the array.
    remaining = window_size - step_size + (len(source) % step_size)
    for offset in range(-remaining, -window_size / 2, step_size):
        frame = np.zeros(window_size)
        frame[:-offset] = source[offset:]
        yield frame


def _moving_average(array, width):
    avg = np.empty_like(array)
    if len(array) > 0:
        avg[0] = array[0]
    for i in range(1, min(width, len(array))):
        avg[i] = avg[i-1] + array[i]
    for i in range(width, len(array)):
        avg[i] = avg[i-1] + array[i] - array[i - width]
    return avg / width


def _moving_maximum(array, width):
    maxes = np.empty_like(array)
    maxindex = len(array)
    half_width = int(width / 2)
    for i in range(maxindex):
        start = max(i - half_width, 0)
        stop = min(start + width, maxindex)
        maxes[i] = array[start:stop].max()
    return maxes


def strength(samples, samplerate):
    """
    Find onset points by measuring spectral flux and looking for peaks.
    Returns an array of sample index numbers.
    """
    # Get a magnitude spectrogram by taking the absolute value of the FFT.
    # The rfft variant truncates the symmetric terms for us.
    # Use a hamming function to balance the weights of samples between pairs
    # of half-overlapped FFT frames.
    mask = np.hamming(WINDOW_SIZE)
    spectrogram = (np.abs(np.fft.rfft(f * mask)) for f in _windows(samples))

    # Compute the spectral flux by subtracting paired spectrum values, then
    # discarding negatives; we only care about flux increases.
    def _flux():
        empty = np.zeros(WINDOW_SIZE / 2 + 1)
        prev = [empty] * (OVERLAP_FACTOR - 1)
        for s in spectrogram:
            yield np.maximum(s - prev.pop(0), 0)
            prev.append(s)
        while prev:
            prev.pop()
            yield empty

    # Compute the onset envelope by aggregating flux across the frequency range.
    # Normalize values onto the 0..1 scale.
    flux = np.fromiter((np.sum(f) for f in _flux()), np.float)
    if len(flux):
        flux -= flux.min()
        flux /= flux.max()
    return flux, float(samplerate) / STEP_SIZE


def events(flux, framerate):
    # Compute the moving average flux value preceding each frame. This sets the
    # threshold for peak prominence. We would normally expect to find a peak no
    # less frequently than 8 Hz, which would be once per beat at 120 BPM, so
    # we'll use a window long enough to include the previous onset peak.
    average = _moving_average(flux, int(framerate / 8 * 1.1))
    # For each frame, compute the maximum flux value across a 50 ms window,
    # which corresponds to the threshold of interval perception. This will be
    # used as a mask to quickly filter for local maxima. 
    maximum = _moving_maximum(flux, int(framerate * 0.025))

    # Events occur at points where the signal is both equal to the local max
    # and significantly greater than the local average.
    threshold = average * 1.5
    onset = flux * (flux == maximum) * (flux >= threshold)

    # Find the frames which still have nonzero values, get their indexes, and
    # convert flux-frame indexes to event times in seconds.
    events = np.unique(np.nonzero(onset)[0])
    return events.astype(np.float) / framerate


def detect(samples, samplerate):
    envelope, framerate = strength(samples, samplerate)
    return events(envelope, framerate)

