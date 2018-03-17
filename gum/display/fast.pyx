#cython: boundscheck=False

cdef extern from "math.h":
    double round (double x) nogil
    double sqrt (double x) nogil

cdef extern from "fast.h":
    ctypedef struct PycairoContext:
      void *ctx
    ctypedef struct argb32:
        unsigned char a, r, g, b

cdef extern from "<cairo.h>":
    void cairo_move_to (void *cr, double x, double y) nogil
    void cairo_line_to (void *cr, double x, double y) nogil
    void cairo_rectangle(void *cr, double x, double ymin,
                         double w, double h) nogil
    void cairo_set_source_rgb (void *cr, double r, double g, double b) nogil
    void cairo_stroke (void *cr) nogil
    void cairo_fill (void *cr) nogil
    void cairo_set_line_width(void *cr, double w) nogil

    ctypedef struct cairo_surface_t
    cairo_surface_t *cairo_image_surface_create(int fmt, int width, int height) nogil
    void cairo_surface_destroy(cairo_surface_t *surface) nogil
    unsigned char *cairo_image_surface_get_data (cairo_surface_t *surface) nogil
    void cairo_surface_mark_dirty (cairo_surface_t *surface) nogil
    void cairo_surface_flush (cairo_surface_t *surface) nogil
    int cairo_image_surface_get_stride(cairo_surface_t *surface) nogil
    int cairo_image_surface_get_height(cairo_surface_t *surface) nogil
    int cairo_image_surface_get_width(cairo_surface_t *surface) nogil
    void cairo_set_source_surface(void *cr, cairo_surface_t *surface, double x, double y) nogil
    void cairo_paint(void *cr) nogil


cdef argb32 blend(argb32 l, argb32 r, float factor):
    cdef argb32 out
    cdef float anti
    anti = 1.0 - factor
    out.a = <int>(l.a * factor + r.a * anti)
    out.r = <int>(l.r * factor + r.r * anti)
    out.g = <int>(l.g * factor + r.g * anti)
    out.b = <int>(l.b * factor + r.b * anti)
    return out


cdef argb32 color(int r, int g, int b):
    cdef argb32 out
    out.a = 255
    out.r = r
    out.g = g
    out.b = b
    return out


cdef argb32 *vfadeup(
        argb32 *buf, int stride, argb32 a, argb32 b, int rows, float power):
    if rows == 0:
        return buf
    if rows == 1:
        buf[0] = blend(a, b, 0.5)
        return buf + stride
    cdef float step, factor
    step = 1.0 / (<float>rows)
    factor = 1.0
    while rows > 0:
        buf[0] = blend(a, b, factor ** power)
        buf += stride
        factor -= step
        rows -= 1
    return buf


cdef argb32 *vfadedown(
        argb32 *buf, int stride, argb32 a, argb32 b, int rows, float power):
    if rows == 0:
        return buf
    if rows == 1:
        buf[0] = blend(a, b, 0.5)
        return buf + stride
    cdef float step, factor
    step = 1.0 / (<float>rows - 1)
    factor = 0
    while rows > 0:
        buf[0] = blend(b, a, factor ** power)
        buf += stride
        factor += step
        rows -= 1
    return buf


def draw_channel(list values, context, float fwidth, float fheight, colors):
    cdef PycairoContext *pcc
    cdef void *cr

    pcc = <PycairoContext *> context
    cr = pcc.ctx

    gridcolor, maincolor, forecolor = colors

    # Line at zero
    cairo_set_line_width(cr, 1)
    cairo_set_source_rgb(cr, gridcolor[0], gridcolor[1], gridcolor[2])
    cairo_move_to(cr, 0, round(height / 2) + 0.5)
    cairo_line_to(cr, width, round(height / 2) + 0.5)
    cairo_stroke(cr)

    if len(values) < 2:
        return

    # Let's try something completely bonkers: render a pixmap and blit,
    # oldschool 2D graphics style.
    cdef cairo_surface_t *surface
    surface = cairo_image_surface_create(0, <int> fwidth, <int> fheight)
    cairo_surface_flush(surface)
    cdef argb32 *buffer, *pixaddr
    cdef int width, height, stride, x, y
    buffer = <argb32*> cairo_image_surface_get_data(surface)
    width = cairo_image_surface_get_width(surface)
    height = cairo_image_surface_get_height(surface)
    stride = cairo_image_surface_get_stride(surface)

    cdef float vscale
    vscale = (<float>(height-1)) / 2.0
    # Convert the input colors from floats into 8-bit integers.
    cdef argb32 rgb_main, rgb_dim, rgb_fore
    # The "dim" color is fully transparent.
    rgb_dim = color(0,0,0)
    rgb_dim.a = 0
    rgb_main = color(maincolor[0]*255, maincolor[1]*255, maincolor[2]*255)
    rgb_fore = color(forecolor[0]*255, forecolor[1]*255, forecolor[2]*255)

    # Draw a line along the mean. This is a fallback for low density levels to
    # ensure that something always gets drawn.
    cairo_set_source_rgb(cr, maincolor[0], maincolor[1], maincolor[2])
    cairo_move_to(cr, 0, -values[0][2] * vscale + vscale)
    for i in range(1, len(values)):
        cairo_line_to(cr, i, -values[i][2] * vscale + vscale)
    cairo_stroke(cr)

    y = 0
    stride /= 4 # sizeof rgba32
    cdef int ymax, ymin, ymean, topdev, botdev
    cdef double mini, maxi, mean, dev
    cdef argb32 meancol
    x = 0
    for mini, maxi, mean, dev in values:
        # the crest factor is peak amplitude divided by average power
        peak = max(abs(maxi), abs(mini))
        crest = peak / dev if dev > 0 else 1.0

        # the mean color fades toward white as the power increases
        meancol = blend(rgb_main, rgb_fore, 1.0/crest)

        # Draw a sequence of four gradients illustrating the distribution.
        ymax = <int> round((1 - maxi) * vscale)
        ymean = <int> ((1 - mean) * vscale)
        ymin = <int> round((1 - mini) * vscale)
        topdev = <int> (ymean - (dev * vscale))
        botdev = <int> (ymean + (dev * vscale))

        # Fade up from the high peak to the power band, then up to the mean.
        pixaddr = &buffer[ymax*stride + x]
        fade = 2.0 / crest
        pixaddr = vfadeup(pixaddr, stride, rgb_dim, rgb_main, topdev-ymax, fade)
        pixaddr = vfadedown(pixaddr, stride, rgb_main, meancol, ymean-topdev, fade)

        # Fade down to the other side of the power band, then to the low peak.
        fade = crest / 2.0
        pixaddr = vfadedown(pixaddr, stride, meancol, rgb_main, botdev-ymean, fade)
        pixaddr = vfadeup(pixaddr, stride, rgb_main, rgb_dim, ymin-botdev, fade)

        x += 1

    cairo_surface_mark_dirty(surface)
    cairo_set_source_surface(cr, surface, 0, 0)
    cairo_paint(cr)
    cairo_surface_destroy(surface)

