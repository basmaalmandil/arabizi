"""Reproducible CPU benchmarks; no third-party packages or network required."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import random
import statistics
import sys
from time import perf_counter_ns

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arabizi import VM, compile_source
from arabizi.compiler import frontend
from arabizi.interpreter import Interpreter

WORKLOADS = {
    "constant_loop": ('''dallah bidaya() -> faragh {
        khalli i: raqm=0; khalli total: raqm=0;
        talama(i<5000) { total=total + i % ((2+3)*(4+5)); i=i+1; }
        itba(total);
    }''', str(sum(i % 45 for i in range(5000)))),
    "function_calls": ('''dallah square(n: raqm)->raqm { arja n*n; }
    dallah bidaya()->faragh {
        khalli i: raqm=0; khalli total: raqm=0;
        talama(i<1500) { total=total+square(i); i=i+1; } itba(total);
    }''', str(sum(i*i for i in range(1500)))),
    "recursive_fibonacci": ('''dallah fib(n: raqm)->raqm {
        itha(n<2) { arja n; } willa { arja fib(n-1)+fib(n-2); }
    }
    dallah bidaya()->faragh { itba(fib(16)); }''', '987'),
}


def timed(fn):
    start = perf_counter_ns()
    fn()
    return (perf_counter_ns()-start)/1_000_000


def summary(samples):
    return {"median_ms": statistics.median(samples), "min_ms": min(samples),
            "max_ms": max(samples), "stdev_ms": statistics.stdev(samples) if len(samples)>1 else 0,
            "samples_ms": samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeats', type=int, default=9)
    parser.add_argument('--output', type=Path, default=Path('benchmarks/results.json'))
    args = parser.parse_args()
    if args.repeats < 3: parser.error('--repeats must be at least 3')
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "platform": platform.platform(),
              "machine": platform.machine(), "processor": platform.processor(),
              "repeats": args.repeats, "warmups": 2, "order_seed": 2030,
              "method": "Precompiled/parsed execution; fresh VM/interpreter per run; output checked; shuffled engine order; wall-clock milliseconds.",
              "workloads": {}}
    rng = random.Random(2030)
    for name, (source, expected) in WORKLOADS.items():
        tree = frontend(source)
        plain, optimized = [compile_source(source, optimize=o) for o in (False, True)]
        programs = {'vm_unoptimized': plain, 'vm_optimized': optimized}
        steps = {}
        def execute(engine):
            output = []
            if engine == 'tree_interpreter': runner = Interpreter(tree, output.append)
            else: runner = VM(programs[engine], output.append)
            runner.run()
            if output != [expected]: raise AssertionError((name, engine, output, expected))
            if engine != 'tree_interpreter': steps[engine] = runner.steps
        samples = {key: [] for key in ['tree_interpreter', *programs]}
        for _ in range(2):
            for engine in samples: execute(engine)
        for _ in range(args.repeats):
            engines = list(samples)
            rng.shuffle(engines)
            for engine in engines: samples[engine].append(timed(lambda: execute(engine)))
        measurements = {key: summary(values) for key, values in samples.items()}
        optimized_ms = measurements['vm_optimized']['median_ms']
        result = {"source": source, "expected_output": expected, "execution": measurements,
                  "compile_optimized": summary([timed(lambda: compile_source(source)) for _ in range(args.repeats)]),
                  "instruction_counts": steps,
                  "static_instructions": {key: sum(len(f.code) for f in p.functions.values()) for key, p in programs.items()},
                  "speedup_vs_tree": measurements['tree_interpreter']['median_ms']/optimized_ms,
                  "speedup_vs_unoptimized": measurements['vm_unoptimized']['median_ms']/optimized_ms}
        report['workloads'][name] = result
        print(f"{name:22} tree={measurements['tree_interpreter']['median_ms']:8.3f}ms  "
              f"VM={optimized_ms:8.3f}ms  vs tree={result['speedup_vs_tree']:.2f}x  "
              f"vs unoptimized={result['speedup_vs_unoptimized']:.2f}x")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f'Raw samples: {args.output}')


if __name__ == '__main__': main()
