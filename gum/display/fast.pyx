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


cdef argb32 *vlerp(argb32 *buf, int stride, argb32 a, argb32 b, int rows):
    if rows == 0:
        return buf
    if rows == 1:
        buf[0] = blend(a, b, 0.5)
        return buf + stride
    cdef float step, factor
    step = 1.0 / (<float>rows-1)
    factor = 1.0
    while rows > 0:
        buf[0] = blend(a, b, factor)
        buf += stride
        factor -= step
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
    rgb_fore = color(forecolor[0]*255, forecolor[1]*255, forecolor[1]*255)

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
    cdef double mini, maxi, mean, std, kurt
    cdef argb32 edgecol, meancol, stdcol
    cdef double kurt_scale
    x = 0
    for mini, maxi, mean, std, kurt in values:
        # the kurtosis controls the slope of the color gradient
        if kurt < 3:
            # flatter distribution as the numbers decrease:
            # de-emphasize the mean
            kurt_scale = kurt / 3.0
            meancol = blend(rgb_fore, rgb_main, kurt_scale)
            edgecol = rgb_dim
            stdcol = blend(meancol, rgb_main, kurt_scale)
        else:
            # peakier distribution as the numbers increase:
            # de-emphasize the edges
            kurt_scale = 1.0 / (kurt - 2.0)
            edgecol = rgb_dim
            meancol = rgb_fore
            stdcol = blend(rgb_main, rgb_dim, kurt_scale)
        # Draw a sequence of four gradients, from the edge to the standard
        # deviation mark, to the mean, to the other edge of the std dev, then
        # down to the far limit.
        ymin = <int> round((1 - mini) * vscale)
        ymax = <int> round((1 - maxi) * vscale)
        ymean = <int> ((1 - mean) * vscale)
        topdev = <int> (ymean - (std * vscale))
        botdev = <int> (ymean + (std * vscale))

        pixaddr = &buffer[ymax*stride + x]
        pixaddr = vlerp(pixaddr, stride, edgecol, stdcol, topdev-ymax)
        pixaddr = vlerp(pixaddr, stride, stdcol, meancol, ymean-topdev)
        pixaddr = vlerp(pixaddr, stride, meancol, stdcol, botdev-ymean)
        pixaddr = vlerp(pixaddr, stride, stdcol, edgecol, ymin-botdev)
        x += 1
    cairo_surface_mark_dirty(surface)
    cairo_set_source_surface(cr, surface, 0, 0)
    cairo_paint(cr)
    cairo_surface_destroy(surface)


import numpy
cimport numpy
DTYPE = numpy.float64
ctypedef numpy.float64_t DTYPE_t

def condense(numpy.ndarray[DTYPE_t, ndim=1] data,
              int start, int width, float density):
    """
    Returns a list of (min, max, mean, std, kurtosis) tuples, describing each
    cell in the view of this data which scales by the given density factor and
    runs for 'width' slices after 'start'.
    The statistical algorithm is based on the online_kurtosis example here:
    https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance

    """
    cdef Py_ssize_t i, j, a, b, l
    cdef double x, n, n1, delta, delta2, delta_n, delta_n2, M2, M3, M4
    cdef double mini, maxi, mean, dev, kurt
    res = []
    l = len(data)
    for i in range(start, start + width):
        with nogil:
            # oversample by 50% to reduce aliasing
            a = <int> round((i - 0.25) * density)
            b = <int> round((i + 1.25) * density)
            if a < 0: a = 0
            if a >= l: break
            if b > l: b = l
            mini = data[a]
            maxi = data[a]
            mean, std, kurt = 0, 0, 3
            n, M2, M3, M4 = 0, 0, 0, 0
            for j in range(a, b):
                x = data[j]
                if x > maxi:
                    maxi = x
                if x < mini:
                    mini = x
                n1 = n
                n += 1
                delta = x - mean
                delta_n = delta / n
                delta_n2 = delta_n * delta_n
                term1 = delta * delta_n * n1
                mean += delta_n
                M4 += term1 * delta_n2 * (n*n - 3*n + 3)
                M4 += 6 * delta_n2 * M2
                M4 += -4 * delta_n * M3
                M3 += term1 * delta_n * (n - 2)
                M3 += -3 * delta_n * M2
                M2 += term1
            # if we only had one sample then it is obviously the mean
            if n < 2: mean = mini
            # deviation is zero if all the samples are the same sample
            dev = sqrt(M2 / (n - 1)) if n > 1 else 0
            # kurtosis of a normal distribution is 3 so use that as fallback
            kurt = (n * M4) / (M2 * M2) if M2 > 0 else 3
        res.append((mini, maxi, mean, dev, kurt))
    return res
