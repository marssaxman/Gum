# Use 'cython2' if present on this system; otherwise fall back to 'cython'.
CYTHON := $(if $(shell command -v cython2 2>/dev/null), cython2, cython)

all: fast.so

fast.so: fast.c
	gcc -shared -pthread -fPIC -fwrapv -O2 -Wall -fno-strict-aliasing \
            -I/usr/include/python2.5 -I/usr/include/python2.6 \
            -I/usr/include/python2.7 \
            `pkg-config --cflags cairo` \
            -o fast.so fast.c \
            `pkg-config --libs cairo`
	if [ ! -e ../fast.so ]; then ln -s fast/fast.so ../; fi

fast.c: fast.pyx
	$(CYTHON) fast.pyx

clean:
	rm -f fast.so fast.c
