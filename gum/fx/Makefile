# Use 'cython2' if present on this system; otherwise fall back to 'cython'.
CYTHON := $(if $(shell command -v cython2 2>/dev/null), cython2, cython)

all: _svf.so

_svf.so: _svf.c
	gcc -shared -pthread -fPIC -fwrapv -O2 -Wall -fno-strict-aliasing \
            -I/usr/include/python2.5 -I/usr/include/python2.6 \
            -I/usr/include/python2.7 \
            -o _svf.so _svf.c

_svf.c: _svf.pyx
	$(CYTHON) _svf.pyx

clean:
	rm -f _svf.so _svf.c
