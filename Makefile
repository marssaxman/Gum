all: fast svf

.PHONY: clean build fast svf

build:
	./build.sh

fast:
	make -C gum/display

svf:
	make -C gum/fx

clean:
	find . -name "*.pyc" | xargs -r rm
	make -C gum/display clean
	make -C gum/fx clean

