import colorsys
from overview import Overview
try:
    from fast import draw_channel
except ImportError:
    from slow import draw_channel


class Display(object):

    def __init__(self, sound):
        self._sound = sound
        self._overview = Overview(sound)
        self.changed = self._overview.changed
        hue = 212.0 / 365.0
        gridcolor = (0.2, 0.2, 0.2)
        maincolor = colorsys.hls_to_rgb(hue, 0.5, 1.0)
        forecolor = colorsys.hls_to_rgb(hue, 0.75, 1.0)
        self._colors = (gridcolor, maincolor, forecolor)

    def set(self, start, width, density):
        self._overview.set(start, width, density)

    def draw(self, context, width, height):
        data = self._overview.get()
        numchan = len(data)
        if numchan > 1:
            height /= numchan
        context.save()
        for channel in data:
            draw_channel(channel, context, width, height, self._colors)
            context.translate(0, height)
        context.restore()

