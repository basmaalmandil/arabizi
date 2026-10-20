# Arabizi · عربيزي

A working, statically typed programming language with Arabic-inspired syntax, an original compiler, and a bytecode virtual machine. Write programs using Latin transliterations, Arabic keywords, or both. Inspect every stage from source tokens to executing instructions.

```text
source → lexer → parser → typed AST → symbolic stack IR → bytecode → VM
```

The Saudi identity comes through the language vocabulary, Arabic examples, and a Riyadh transit-planning demo. The transit data is illustrative. This is an educational systems project with explicit semantics and measured limitations.

## Run it

Python 3.9 or newer. No runtime dependencies, API keys, network calls, or installation needed.

```sh
python3 -m arabizi run examples/riyadh.az
python3 demo.py
python3 -m unittest discover -s tests -v
```

Run these commands from this directory. Optional installation: `python3 -m pip install -e .`, after which `arabizi` replaces `python3 -m arabizi`. Installation may download build tooling; direct execution does not.

## A complete program

```text
dallah fare(stops: raqm) -> raqm {
    itha (stops <= 3) {
        arja 4;
    } willa {
        arja 4 + stops;
    }
}

dallah bidaya() -> faragh {
    khalli trip: raqm = 1;
    talama (trip <= 5) {
        itba(fare(trip));
        trip = trip + 1;
    }
}
```

Functions, recursion, mutable variables, lexical scopes, conditions, loops, strings, integer and floating arithmetic, booleans, and short-circuit operators are implemented. Every variable and function signature has an explicit type. The compiler rejects use before declaration, bad arguments, inconsistent types, missing returns, and unreachable statements.

## Make the engineering visible

```sh
python3 -m arabizi tokens examples/riyadh.az
python3 -m arabizi ast examples/riyadh.az
python3 -m arabizi check examples/riyadh.az
python3 -m arabizi ir examples/riyadh.az
python3 -m arabizi disasm examples/riyadh.az
python3 -m arabizi compile examples/riyadh.az -o /tmp/riyadh.azbc
python3 -m arabizi run /tmp/riyadh.azbc
python3 -m arabizi run examples/factorial.az --trace
python3 -m arabizi run examples/riyadh.az --no-opt
```

The `.azbc` file contains versioned JSON bytecode and source maps. Loading checks opcode operands, branch targets, call signatures, operand-stack heights, and local initialization. Execution uses an iterative VM with explicit call frames; no `eval`, `exec`, Python code generation, or parser generator is used.

Errors carry a phase, file, line, column, and source underline:

```text
examples/type_error.az:2:5: type: Expected raqm, got nass
      khalli trips: raqm = "five";
      ^^^^^^
```

```text
examples/runtime_error.az:3:14: runtime: Division by zero
      itba(100 / passengers);
               ^
```

`python3 demo.py` walks through source, tokens, typed symbols, symbolic IR, assembled instructions, a serialized round trip, execution, and both kinds of error. A captured run is in [docs/demo-transcript.txt](docs/demo-transcript.txt).

## Arabic and Latin vocabulary

| Meaning | Latin | Arabic |
| --- | --- | --- |
| Function | `dallah` | `دالة` |
| Variable | `khalli` | `متغير` |
| If / else | `itha` / `willa` | `إذا` / `وإلا` |
| While | `talama` | `طالما` |
| Return / print | `arja` / `itba` | `ارجع` / `اطبع` |
| Integer / float | `raqm` / `kasr` | `رقم` / `كسر` |
| String / boolean / void | `nass` / `mantiq` / `faragh` | `نص` / `منطق` / `فراغ` |
| True / false | `sah` / `khata` | `صح` / `خطأ` |
| And / or / not | `wa` / `aw` / `mish` | `و` / `أو` / `ليس` |
| Entry point | `bidaya` | `بداية` |

These are this language's chosen spellings, not a claim of standardized Arabizi transliteration. See [the language specification](docs/language.md) for all aliases, grammar, and numeric behavior. Try `python3 -m arabizi run examples/arabic.az` for Arabic identifiers and Arabic-Indic digits.

## Tests and measurements

The test suite covers the front end, semantic errors, evaluation order, short-circuit side effects, scopes, recursion deeper than Python's usual call-stack limit, artifact validation, CLI behavior, generated arithmetic trees, and generated loop checksums. Successful programs are checked across optimized VM, unoptimized VM, saved/reloaded bytecode, and the tree interpreter.

```sh
python3 -m unittest discover -s tests -v
python3 benchmarks/run.py --repeats 9
```

On the recorded Python 3.9.6/macOS arm64 run, constant folding cut the constant-loop VM instruction count by **28.6%** and improved execution **1.39×** against unoptimized bytecode. The optimized VM was roughly tied with the tree interpreter on that workload and slower on the other two. See [benchmark methodology and results](docs/benchmarks.md) and [raw samples](benchmarks/results.json). These are small local workloads, not a claim of general speed superiority.

## Repository guide

| File | Responsibility |
| --- | --- |
| `arabizi/lexer.py` | Tokenization, aliases, literals, comments, source locations |
| `arabizi/parser.py` | Grammar and expression precedence |
| `arabizi/semantic.py` | Types, symbols, scopes, local slots, return analysis |
| `arabizi/compiler.py` | Constant folding, symbolic IR, label assembly |
| `arabizi/bytecode.py` | Artifact decoding and control-flow verification |
| `arabizi/vm.py` | Operand stacks, call frames, execution budgets, tracing |
| `arabizi/interpreter.py` | Tree-walking execution baseline |
| `tests/test_language.py` | Behavioral, differential, diagnostic, artifact, and CLI tests |
| `benchmarks/run.py` | Correctness-checked benchmark harness |

Read [architecture and trade-offs](docs/architecture.md) and [what the measurements changed](docs/engineering-notes.md).

## Continuous integration

The [GitHub Actions template](docs/github-actions-ci.yml) runs tests, the demo, and benchmark checks on Python 3.9, 3.12, and 3.13. To activate it, place the file at `.github/workflows/ci.yml` using a GitHub connection with workflow permission. It is stored as a template because the publishing connection does not have that permission.

## Scope

This version has no arrays, objects, closures, module system, input primitive, native code backend, debugger UI, or concurrency. Top-level declarations are functions only. The VM limits instructions and call depth, but does not enforce memory or wall-clock quotas. Source compilation and bytecode verification are also not resource sandboxes. Run trusted local programs and artifacts.

The supplied [Tiny_Compiler reference](https://github.com/Abdelrhman-Sayed70/Tiny_Compiler) advertises a scanner and parser. This repository is a separate implementation; no code was copied from it. The comparison establishes scope, not a benchmark against that project.
