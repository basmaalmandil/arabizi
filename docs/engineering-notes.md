# Engineering notes: what worked, what fell short

## The performance expectation did not hold

A stack VM with indexed locals might be expected to beat a tree walker that recursively dispatches nodes and searches dictionaries. The measured results do not support that blanket claim: the optimized VM was approximately tied on the arithmetic loop and slower on function-call and recursive workloads. Bytecode introduces more dispatch steps per source operation, and explicit frames have allocation costs. These are hypotheses to profile, not proven bottlenecks.

The concrete improvement implemented here is constant folding. It removes 30,000 dynamic instructions from the supplied loop and produced a 1.39× median speedup against unoptimized VM execution in the recorded run. It does not help workloads without constant expression subtrees. The benchmark report keeps the unfavorable comparisons alongside this gain.

## Correctness shaped the implementation

These are design decisions and verified edge cases, not a claim that every alternative below was implemented and later reverted:

- **Short-circuiting needs control flow.** Compiling both sides to an ordinary binary operation would call functions and raise arithmetic errors that the language says to skip. `DUP` plus conditional jumps preserves side effects and a single result. Tests check both calls and division by zero on skipped branches.
- **Python booleans need an explicit language type.** Python's boolean/integer relationship cannot define this language's static rules. Literal typing uses exact host types, and semantic analysis rejects mixed boolean/integer operations.
- **Integer division must not use floats.** Converting a huge integer division result through a float loses precision. Magnitude division and sign restoration preserve truncation toward zero. Tests include negative operands and integers larger than binary64 can exactly represent.
- **Language calls should not consume Python call frames.** Explicit VM frames let the recursive demo exceed 1,000 nested calls when the configured language limit allows it. The benchmark interpreter still uses Python recursion and is not the production execution path.
- **Successful compilation is not enough for an artifact loader.** Saved bytecode can be truncated or modified. The reader checks control flow, stack consistency, signatures, and initialized locals before execution. This provides useful corruption diagnostics while remaining clearly short of a security sandbox.

## What validation establishes

The suite exercises three execution paths: optimized bytecode, unoptimized bytecode, and a tree interpreter. Bytecode also makes a serialization/verification round trip. One hundred seeded arithmetic expression trees have independently computed expected values, and twenty generated loop programs check closed-form-style sums via host arithmetic. Source error fixtures cover each compiler stage, and CLI tests check exit codes and readable failures.

Sharing the lexer, parser, type checker, and arithmetic helper means differential testing cannot independently validate every language rule. Explicit expected-output cases, rejected-program cases, and source-span checks complement it. The CI template in `docs/github-actions-ci.yml` targets Python 3.9, 3.12, and 3.13; local validation in this delivery used 3.9.6. The publishing GitHub connection lacks workflow permission, so the configuration is included as a template rather than an active workflow. Remote CI has not run.

## Deliberate omissions and next experiments

There is no register allocator, native backend, SSA representation, or speculative optimization. Those would increase project scope without evidence that this language needs them yet. Useful next work would be a profiler-guided dispatch experiment, a larger benchmark corpus, stronger typed artifact verification, multiple-error parser recovery, and richer Arabic editor integration. Memory quotas and compilation budgets would be required before exposing this compiler to untrusted public input.

The current deliverable is a complete small compiler pipeline and an inspectable execution model. Its limitations and measured results are part of the engineering result.
