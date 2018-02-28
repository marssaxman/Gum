#include <Python.h>

typedef struct {
  PyObject_HEAD
  void *ctx;
} PycairoContext;

typedef struct {
    unsigned char b, g, r, a;
} argb32;
