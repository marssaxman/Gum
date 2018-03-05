import numpy as np


def _onset_strength(signal, samplerate, step_size=512):
    # Generate a simple spectral flux envelope suitable for tempo detection.
    # Returns an array of onset strength values and the frame rate used.
    spectrogram = []
    for offset in range(0, len(signal) - len(signal) % step_size, step_size):
        f = signal[offset:offset+step_size]
        spectrogram.append(np.abs(np.fft.rfft(f)))
    flux = []
    for i in range(len(spectrogram)-1):
        flux.append(np.maximum(spectrogram[i+1] - spectrogram[i], 0))
    envelope = np.zeros(len(flux), np.float)
    for i, frame in enumerate(flux):
        envelope[i] = np.sum(frame)
    if envelope.size:
        envelope -= envelope.min()
        envelope /= envelope.max()
    return envelope, float(samplerate) / step_size


def detect(samples, samplerate):
    # It is actually cheaper to generate a low-resolution onset envelope here
    # than it would be to perform autocorrelation on the higher-resolution data
    # we have likely already generated during note-onset detection.
    envelope, framerate = _onset_strength(samples, samplerate)
    # Look for patterns of activations in this envelope signal which are
    # likely to correlate with the musical tempo.
    # We will use an 8-second autocorrelation window so we can still capture
    # a significant number of low-tempo beat events. This must be rounded to
    # an even number of envelope frames; in fact we will round it up to the
    # next power of 2 for fast FFTs.
    window_size = int(8.0 * framerate)
    window_mask = np.hanning(window_size)

    # Our model holds that the average tempo is 120 BPM, and that tempos
    # follow a log-normal distribution around that mean.
    bpm_mean, bpm_std = 120.0, 1.0
    bpms = np.empty(window_size, dtype=np.float)
    bpms[0] = np.inf
    bpms[1:] = framerate / np.arange(1.0, window_size) * 60.0
    weight = np.exp(-0.5 * ((np.log2(bpms) - np.log2(bpm_mean)) / bpm_std)**2)

    # Divide the signal into evenly sized windows; autocorrelate each one,
    # accumulating the amplitudes into a histogram of tempo probabilities.
    tempogram = np.zeros(window_size, np.float)
    windows = 1 + len(envelope) - window_size
    for i in range(windows):
        frame = envelope[i:i + window_size] * window_mask
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[corr.size / 2:]
        tempogram += corr / np.max(np.abs(corr))
    tempogram /= float(windows)

    # Weight the frequency peaks by the probability distribution, then select
    # the best remaining candidate. The corresponding BPM value is our result.
    return bpms[np.argmax(tempogram * weight)]

