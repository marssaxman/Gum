import colorsys
from . import draw_channel

class Display(object):

    def __init__(self, data):
        self._data = data
        hue = 212.0 / 365.0
        gridcolor = (0.2, 0.2, 0.2)
        maincolor = colorsys.hls_to_rgb(hue, 0.5, 1.0)
        forecolor = colorsys.hls_to_rgb(hue, 0.75, 1.0)
        self._colors = (gridcolor, maincolor, forecolor)

    def draw(self, context, width, height):
        numchan = len(self._data)
        if numchan > 1:
            height /= numchan
        context.save()
        for channel in self._data:
            draw_channel(channel, context, width, height, self._colors)
            context.translate(0, height)
        context.restore()

