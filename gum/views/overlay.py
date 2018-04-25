import gtk
import gobject
import cairo


class _CairoWidget(gtk.DrawingArea):
    """A drawing area providing a Cairo context.

    Manages redraw mechanics and clips the drawing context to fit the
    widget frame. A subclass need only implement the draw() method and fill
    the context, using the requested width and height in context coordinates.
    """
    __gsignals__ = {"expose-event": "override"}

    def __init__(self):
        super(_CairoWidget, self).__init__()
        self._redrawing = False

    def do_expose_event(self, event):
        context = self.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        width, height = self.window.get_size()
        self.draw(context, width, height)
        self._redrawing = False

    def redraw(self):
        # queue_draw() emits an expose event. Double buffering is used
        # automatically in the expose event handler.
        if not self._redrawing:
            self._redrawing = True
            self.queue_draw()

    def draw(self, context, width, height):
        """Must be overriden to draw to the cairo context."""
        raise NotImplemented


class Canvas(_CairoWidget):
    """A widget which overlays graphic layers.

    This widget paints itself by successively passing its context to
    layer objects. The draw() method of a layer object must paint to
    the context.

    """
    def __init__(self):
        super(Canvas, self).__init__()
        self.layers = []
        self.connect("destroy", self.on_destroy)
        self.emit("destroy")

    def draw(self, context, width, height):
        for layer in self.layers:
            layer.stack(context, width, height)

    def on_destroy(self, widget):
        # Lose the references to Layers objects, otherwise they do not
        # get garbage-collected. I suspect a strange interaction
        # between the gobject and the Python reference counting
        # systems.
        self.layers = []



class Layer(object):
    """Abstract base class for layers used with the Canvas.

    Implement the draw() method and paint into the provided context, using
    the specified width and height in context coordinates.
    """
    def __init__(self, layered):
        self._layered = layered

    def stack(self, context, width, height):
        """Paint the layer on top of the passed context."""
        context.set_operator(cairo.OPERATOR_OVER)
        self.draw(context, width, height)

    def update(self):
        self._layered.redraw()

    def draw(self, context, width, height):
        raise NotImplemented

