CC ?= cc
CFLAGS ?= -O2 -std=c99 -Wall -Wextra -Werror -pedantic

.PHONY: all test bench clean
all: build/c80-grade

build/c80-grade: src/c80_lut.c src/c80_lut.h src/host.c
	mkdir -p build
	$(CC) $(CFLAGS) src/c80_lut.c src/host.c -o $@

test: all
	python3 -m unittest discover -s tests -v

build/benchmark: src/c80_lut.c src/c80_lut.h src/benchmark.c
	mkdir -p build
	$(CC) $(CFLAGS) src/c80_lut.c src/benchmark.c -o $@

bench: build/benchmark
	./build/benchmark

clean:
	rm -rf build
