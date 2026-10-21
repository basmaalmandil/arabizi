# Contributing to Arabizi

## Local setup

Use Python 3.9 or newer. From the repository root, run:

```sh
python3 -m unittest discover -s tests -v
python3 demo.py
```

Direct execution needs no installation or third-party runtime dependencies. Optional editable installation is available with `python3 -m pip install -e .`; this may download build tooling.

## Finding the relevant code

- Tokenization and keyword aliases: [arabizi/lexer.py](arabizi/lexer.py).
- Grammar and precedence: [arabizi/parser.py](arabizi/parser.py).
- Types, scopes, and return analysis: [arabizi/semantic.py](arabizi/semantic.py).
- Lowering and constant folding: [arabizi/compiler.py](arabizi/compiler.py).
- Artifact validation: [arabizi/bytecode.py](arabizi/bytecode.py).
- Execution: [arabizi/vm.py](arabizi/vm.py).
- Behavioral tests: [tests/test_language.py](tests/test_language.py).

Read the [language specification](docs/language.md) and [architecture](docs/architecture.md) before changing language behavior.

## Preparing a change

Keep each pull request focused on one problem. Describe the behavior before and after the change and include a small reproducing program when relevant.

For compiler or runtime changes, add a regression test and check behavior with and without constant folding. The existing suite also compares VM execution, serialized bytecode, and the tree interpreter; extend those checks when they apply to the change.

Update the language specification when syntax or semantics change. Keep Arabic and Latin keyword forms in mind when changing the front end.

For performance changes, use the [benchmark methodology](docs/benchmarks.md):

```sh
python3 benchmarks/run.py --repeats 9
```

Report the Python version, platform, workload, and measurements alongside any performance claim.

## Reporting a problem

Include:

- Python version and operating system.
- The exact command, run from the repository root.
- A minimal source program or trusted artifact that reproduces the problem.
- Expected output and the complete actual diagnostic.

Remove credentials and personal data from examples before sharing them.
