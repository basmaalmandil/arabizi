# Benchmarks

Run from the repository root:

```sh
python3 benchmarks/run.py --repeats 9
```

The harness writes all samples, source programs, expected outputs, Python/platform metadata, instruction counts, and aggregate statistics to `benchmarks/results.json`. Use `--output /tmp/arabizi-results.json` to retain the checked-in run. There are no external packages or data downloads.

## Recorded local run

Environment: Python 3.9.6, macOS 26.5.1, arm64. Nine timed runs per engine/workload after two warmups. Times below are medians rounded to three decimals. Consult the JSON for the precise environment timestamp, sample spread, and unrounded values.

| Workload | Tree interpreter | Optimized VM | VM speedup vs tree | VM speedup vs unoptimized VM |
| --- | ---: | ---: | ---: | ---: |
| Constant arithmetic in 5,000 loop iterations | 25.343 ms | 25.634 ms | 0.99× | 1.39× |
| 1,500 function calls | 8.476 ms | 10.000 ms | 0.85× | 0.99× |
| Recursive Fibonacci(16) | 11.158 ms | 12.775 ms | 0.87× | 0.99× |

A ratio above 1 means the optimized VM was faster. The 0.99× ratios should be treated as approximately tied in this small sample. The VM does not outperform the tree interpreter across these workloads.

| Workload | Unoptimized executed instructions | Optimized executed instructions | Optimized compile median |
| --- | ---: | ---: | ---: |
| Constant loop | 105,012 | 75,012 | 0.150 ms |
| Function calls | 27,012 | 27,012 | 0.165 ms |
| Recursive Fibonacci | 31,931 | 31,931 | 0.136 ms |

The constant loop executes six fewer instructions per iteration: `((2+3)*(4+5))` becomes one constant. That is 30,000 fewer instructions, a **28.6% reduction**. The other workloads have no foldable multi-operator literal expression, so the optimizer does not reduce their instruction counts. This explains the limited scope of the optimization's benefit.

## Method

Three implementations execute exactly the same checked program: a tree interpreter, unoptimized bytecode, and optimized bytecode. Parsing/compilation happens outside execution timing. Each run creates a fresh interpreter or VM, collects its output in memory, and checks an independently specified expected checksum. Program output is never printed inside the measured region. Result validation, runner construction, and output capture are included for all engines.

Engine order is shuffled per repetition using seed 2030. The harness retains Python's normal garbage-collection behavior and separately times complete optimized compilation. Instruction counts are deterministic; elapsed times are not. The raw result includes minima, maxima, standard deviations, medians, and individual samples.

## Interpretation and limits

The VM runs in Python and dispatches many stack operations for a single AST operation. The tree interpreter has recursive evaluation and dictionary scope lookup, while the VM has explicit frame allocation and per-instruction budget accounting. Their balance depends on the workload. Dispatch/frame overhead is a plausible explanation for these results, not a measured profiler attribution.

This is a same-language execution baseline, not a comparison with a native compiler or CPython executing equivalent Python. The suite is small, fits in memory, uses fixed inputs, and measures one local environment. It does not measure parsing throughput across large corpora, peak memory, startup time, adversarial programs, or statistical significance. No universal speedup is claimed. Future performance changes should add representative workloads and profiling evidence before changing the architecture.
