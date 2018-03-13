# Simple interface for reading and writing sound files in a variety of formats.
# Uses pysndfile if possible; falls back to ffmpeg if necessary.

import pysndfile
from collections import namedtuple

AudioFile = namedtuple('AudioFile', 'data samplerate format')


def list_extensions():
    extensions = pysndfile.get_sndfile_formats()
    extensions.append('aif')
    return extensions


def read(filename):
    f = pysndfile.PySndfile(filename)
    nframes = f.frames()
    return AudioFile(f.read_frames(nframes), f.samplerate(), f.format())


def write(filename, contents):
    channels = contents.data.ndim
    format = contents.format
    f = pysndfile.PySndfile(
        filename,
        mode='w',
        format=format,
        channels=contents.data.ndim,
        samplerate=contents.samplerate
    )
    f.write_frames(contents.data)

