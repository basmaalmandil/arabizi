# Troubleshooting Arabizi

Run the commands below from the repository root with Python 3.9 or newer.

## Python cannot find the module

If `python3 -m arabizi` reports `No module named arabizi`, change to the directory containing `pyproject.toml` and the `arabizi/` package, then try:

```sh
python3 -m arabizi --help
python3 -m arabizi run examples/riyadh.az
```

If the standalone `arabizi` command is unavailable, use `python3 -m arabizi` directly. The standalone command requires installation; see [the setup instructions](README.md#run-it).

## File paths and text encoding

Input paths are resolved relative to the current working directory. Check the path in your command if a file cannot be found. Source and bytecode files are read as UTF-8.

The compiler writes to the path passed with `-o` but does not create missing parent directories. Choose an existing directory:

```sh
python3 -m arabizi compile examples/riyadh.az -o riyadh.azbc
python3 -m arabizi run riyadh.azbc
```

## Syntax, type, and runtime errors

Start with a syntax and type check:

```sh
python3 -m arabizi check examples/riyadh.az
```

A successful check prints `OK: syntax and types verified`. It does not execute the program or guarantee that execution will succeed. For example, division by zero is a runtime error.

Diagnostics identify the phase and, when available, the source location. These supplied programs deliberately demonstrate failures:

```sh
python3 -m arabizi check examples/type_error.az
python3 -m arabizi run examples/runtime_error.az
```

Both commands are expected to return a nonzero exit status. Correct the indicated source expression and rerun the check or program.

## Instruction and call-depth limits

The default execution budgets are 1,000,000 instructions and 1,024 active call frames.

For `Instruction budget exceeded`, first check whether a loop can terminate. For `Call depth exceeded`, check the recursion's base case. If a trusted program legitimately needs a larger budget, set positive integer limits:

```sh
python3 -m arabizi run examples/factorial.az --max-steps 2000000 --max-frames 2048
```

These limits do not enforce memory or wall-clock quotas. See [the execution boundaries](docs/architecture.md#artifact-verification).

## Inspecting execution

Trace instructions with:

```sh
python3 -m arabizi run examples/factorial.az --trace
```

Trace output goes to standard error; program output goes to standard output. To save the trace separately:

```sh
python3 -m arabizi run examples/factorial.az --trace 2> trace.txt
```

Use `--no-opt` with source input to compare behavior without constant folding:

```sh
python3 -m arabizi run examples/riyadh.az --no-opt
```

Loading saved bytecode does not recompile it, so `--no-opt` does not change an existing artifact.

## Working with saved bytecode

Use `run` or `disasm` for a saved `.azbc` artifact:

```sh
python3 -m arabizi disasm riyadh.azbc
```

Use the original `.az` source for syntax/type checking, token inspection, AST inspection, and recompilation. If an artifact is incompatible or damaged, regenerate it from trusted source using the current compiler.

For a reproducible compiler problem, follow the [reporting checklist](CONTRIBUTING.md#reporting-a-problem).
