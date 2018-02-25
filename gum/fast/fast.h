#include <Python.h>

typedef struct {
  PyObject_HEAD
  void *ctx;
} PycairoContext;

