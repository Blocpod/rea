# Host validation record

Executed with the existing host C compiler and Python 3. No extra dependencies
were installed. All results are offline host observations.

- `make test bench`: 8 tests passed in 3.425 seconds. Compiler flags:
  `-O2 -std=c99 -Wall -Wextra -Werror -pedantic`.
- Synthetic benchmark: 2,073,600 pixels, 0.115705 host CPU seconds,
  checksum 203785869259. This is not a camera performance result.
- AddressSanitizer + UndefinedBehaviorSanitizer build: 8 tests passed in 3.662
  seconds with `ASAN_OPTIONS=detect_leaks=0`. The initial default sanitizer run
  could not finish because LeakSanitizer could not read `/proc/<pid>/task` in
  this host environment and reported incompatibility with ptrace. Address and
  undefined-behavior checks remained enabled in the successful run. No leak
  checking claim is made.
- Python compilation: `python3 -m py_compile tools/compile_cube.py
  tools/generate_examples.py tests/test_lut.py` passed.

Coverage includes the actual Python-compiled binary consumed by the actual C
host; 8-bit identity over every component value plus primary corners; RGB
ordering using a channel permutation; independent floating-point trilinear
comparison on nonlinear table values with a nondefault input domain; maximum
dimension 65; corruption/truncation/header rejection; explicit clipping; and
exclusive output creation.

No ARM cross build, camera loader, firmware patch, physical camera execution,
image-quality match, live-preview speed or recording-path integration was
performed. Those claims remain unverified.
