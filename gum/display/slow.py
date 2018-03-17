# Python fallback if we happen not to have compiled the Cython version

def draw_channel(values, context, width, height, colors):
    gridcolor, maincolor, forecolor = colors
    context.save()
    # Center the horizontal axis in the viewing area, then flip it, so that
    # positive coordinates rise above the axis and negative ones drop below.
    height /= 2
    context.translate(0, height)
    context.scale(1.0, -1.0)
    # Line at zero
    context.set_line_width(1)
    context.set_source_rgb(*gridcolor)
    context.move_to(0, 0)
    context.line_to(width, 0)
    context.stroke()
    dlen = len(values)
    if dlen < 2: return
    # Draw the outline of the waveform by filling the shape between its limits.
    context.set_source_rgb(*maincolor)
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
    context.set_source_rgb(*forecolor)
    context.move_to(0, (values[0].mean - values[0].std) * height)
    for i in range(1, dlen):
        context.line_to(i, (values[i].mean - values[i].std) * height)
    for i in range(0, dlen-1):
        context.line_to(width - i, (values[-i].mean + values[-i].std) * height)
    context.close_path()
    context.fill()
    context.restore()

