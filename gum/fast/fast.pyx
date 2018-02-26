#cython: boundscheck=False

cdef extern from "math.h":
    double round (double x) nogil
    double sqrt (double x) nogil

cdef extern from "fast.h":
    ctypedef struct PycairoContext:
      void *ctx

cdef extern from "<cairo.h>":
    void cairo_move_to (void *cr, double x, double y) nogil
    void cairo_line_to (void *cr, double x, double y) nogil
    void cairo_rectangle(void *cr, double x, double ymin,
                         double w, double h) nogil
    void cairo_set_source_rgb (void *cr, double r, double g, double b) nogil
    void cairo_stroke (void *cr) nogil
    void cairo_fill (void *cr) nogil
    void cairo_set_line_width(void *cr, double w) nogil


def draw_channel(list values, context, float width, float height):
    cdef PycairoContext *pcc
    cdef void *cr
    cdef double mini, maxi, mean, std
    cdef double x, ymin, ymax

    pcc = <PycairoContext *> context
    cr = pcc.ctx

    # Line at zero
    cairo_set_line_width(cr, 1)
    cairo_set_source_rgb(cr, 0.2, 0.2, 0.2)
    cairo_move_to(cr, 0, round(height / 2) + 0.5)
    cairo_line_to(cr, width, round(height / 2) + 0.5)
    cairo_stroke(cr)

    # Waveform
    cairo_set_source_rgb(cr, 0.0, 0.47058823529411764, 1.0)
    for x, (mini, maxi, mean, std, kurt) in enumerate(values):
        with nogil:
            # -1 <= mini <= maxi <= 1
            # ystart <= ymin <= ymax <= ystart + height - 1
            ymin = round((-mini * 0.5 + 0.5) * (height - 1))
            ymax = round((-maxi * 0.5 + 0.5) * (height - 1))
            if ymin == ymax:
                # Fill one pixel
                cairo_rectangle(cr, x, ymin, 1, 1)
                cairo_fill(cr)
            else:
                # Draw a line from min to max
                cairo_move_to(cr, x + 0.5, ymin)
                cairo_line_to(cr, x + 0.5, ymax)
                cairo_stroke(cr)


import numpy
cimport numpy
DTYPE = numpy.float64
ctypedef numpy.float64_t DTYPE_t

def _condense(numpy.ndarray[DTYPE_t, ndim=1] data,
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
            a = <int> round(i * density)
            b = <int> round((i + 1) * density)
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
            kurt = (n * M4) / (M2 * M2) if n > 2 else 3
        res.append((mini, maxi, mean, dev, kurt))
    return res
