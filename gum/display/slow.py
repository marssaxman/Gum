# Python fallbacks if we happen not to have compiled the Cython versions

from collections import namedtuple

CellStats = namedtuple('CellStats', 'min max mean std')

def condense(data, start, width, density):
    """
    Scale the data by the density factor and slice it into cells. Compute
    the statistical properties of each cell. Return a list of values, in the
    form of a CellStats tuple.
    """
    res = []
    start = int(start)
    width = int(width)
    dlen = len(data)
    for i in range(start, start + width):
        a = int(round((i - 0.25) * density))
        b = int(round((i + 1.25) * density))
        if a < 0: a = 0
        if a >= dlen: break
        if b > dlen: b = dlen
        d = data[a:b]
        mini = d.min()
        maxi = d.max()
        mean = d.mean() if dlen >= 2 else mini
        std = d.std() if dlen > 2 else 0
        res.append(CellStats(mini, maxi, mean, std))
    return res

def draw_channel(values, context, width, height):
    context.save()
    # Center the horizontal axis in the viewing area, then flip it, so that
    # positive coordinates rise above the axis and negative ones drop below.
    height /= 2
    context.translate(0, height)
    context.scale(1.0, -1.0)
    # Line at zero
    context.set_line_width(1)
    context.set_source_rgb(0.2, 0.2, 0.2)
    context.move_to(0, 0)
    context.line_to(width, 0)
    context.stroke()
    dlen = len(values)
    if dlen < 2: return
    # Draw the outline of the waveform by filling the shape between its limits.
    context.set_source_rgb(0.0, 0.47058823529411764, 1.0)
    context.move_to(0, values[0].min * height)
    for i in range(1, dlen):
        context.line_to(i, values[i].min * height - 0.5)
    for i in range(0, dlen-1):
        context.line_to(width - i, values[-i].max * height + 0.5)
    context.close_path()
    context.fill()
    # Draw a stroke along the mean to ensure that the waveform stays visible
    # even when the limits are very close together and the density is very low.
    context.move_to(0, values[0].mean * height)
    for i in range(1, dlen):
        context.line_to(i, values[i].mean * height)
    context.stroke()
    # Draw again, with a lighter color, filling in the area around the mean
    # for the width of the standard deviation.
    context.set_source_rgb(0.5, 0.737254902, 1.0)
    context.move_to(0, (values[0].mean - values[0].std) * height)
    for i in range(1, dlen):
        context.line_to(i, (values[i].mean - values[i].std) * height)
    for i in range(0, dlen-1):
        context.line_to(width - i, (values[-i].mean + values[-i].std) * height)
    context.close_path()
    context.fill()
    context.restore()

