all: svf

.PHONY: clean build svf

build:
	./build.sh

svf:
	make -C gum/fx

clean:
	find . -name "*.pyc" | xargs -r rm
	make -C gum/fx clean

