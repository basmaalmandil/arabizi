# Language specification · v0.1

## Program structure

A source file is UTF-8, conventionally ending in `.az`. A program contains named functions and exactly one `bidaya() -> faragh` entry point. All functions are collected before body checking, so forward references and mutual recursion work. Functions occupy a separate namespace from local variables. No global variables or nested function declarations exist.

```ebnf
program    = { function } ;
function   = "dallah", identifier, "(", [ parameters ], ")", "->", type, block ;
parameters = parameter, { ",", parameter } ;
parameter  = identifier, ":", type ;
type       = "raqm" | "kasr" | "nass" | "mantiq" | "faragh" ;
block      = "{", { statement }, "}" ;
statement  = block
           | "khalli", identifier, ":", type, "=", expression, ";"
           | identifier, "=", expression, ";"
           | "itha", "(", expression, ")", block, [ "willa", block ]
           | "talama", "(", expression, ")", block
           | "arja", [ expression ], ";"
           | "itba", "(", expression, ")", ";"
           | expression, ";" ;
expression = prefix, { binary-op, prefix } ; (* precedence table below *)
prefix     = ( "-" | "!" | "mish" ), prefix | primary ;
primary    = number | string | "sah" | "khata" | identifier
           | identifier, "(", [ arguments ], ")"
           | "(", expression, ")" ;
arguments  = expression, { ",", expression } ;
```

The expression production is schematic: the precedence table determines grouping. Calls accept function names, not arbitrary callable expressions.

## Types and evaluation

| Type | Values and operations |
| --- | --- |
| `raqm` | Arbitrary-precision integers, subject to host memory/conversion limits; `+ - * / %`, comparisons |
| `kasr` | Finite Python binary64 floats; `+ - * /`, comparisons |
| `nass` | Unicode strings; concatenation with `+`, equality/inequality |
| `mantiq` | `sah` and `khata`; `wa`, `aw`, `mish`, `!`, equality/inequality |
| `faragh` | Void return; not valid as a variable or parameter type |

There are no implicit conversions. `1 + 2.0`, integer conditions, and `sah + 1` fail type checking. Arithmetic requires matching numeric types. Equality requires matching non-void types. String ordering is unsupported. `%` is integer-only.

Integer division truncates toward zero: `-7 / 3 == -2`. Remainder follows `a == (a / b) * b + a % b`; therefore `-7 % 3 == -1`. Integer arithmetic never goes through a floating conversion. Division/modulo by zero is a source-located runtime error. Float overflow to a non-finite result is also a runtime error; out-of-range float literals are lexical errors.

Operand and argument evaluation is left to right. `wa` and `aw` short-circuit, including function side effects. An unused expression value is discarded. A void function falls through to a void return. Non-void functions must visibly return on every path: a return statement or an `itha` with returning branches qualifies. The analysis conservatively assumes a loop can finish, even for `talama(sah)`. Statements after a guaranteed return are rejected. All branches are type-checked, even if a condition is constant.

## Precedence

Listed from lowest to highest. All binary operators associate left; chained comparisons are not special syntax, and will generally fail type checking.

| Level | Operators |
| --- | --- |
| 1 | `aw` |
| 2 | `wa` |
| 3 | `== !=` |
| 4 | `< <= > >=` |
| 5 | `+ -` |
| 6 | `* / %` |
| 7 | Prefix `- ! mish` |
| 8 | Function calls, literals, names, parentheses |

## Lexical rules

Identifiers begin with a Unicode alphabetic character or `_`, followed by Unicode alphanumeric characters or `_`. They are case-sensitive. This intentionally small scanner does not support combining marks in identifiers, Unicode normalization, or transliteration digits at the start of names. Prefer plain, unvowelled Arabic identifiers. Numeric literals use Unicode decimal digits, including Arabic-Indic digits, with an optional ASCII decimal point and a nonempty fractional part. Exponents and leading-dot decimals are unsupported.

Strings use double quotes and support `\n`, `\r`, `\t`, `\"`, and `\\`. Raw newlines are rejected. `//` comments run to newline; `/* ... */` comments may nest. Keywords and operators inside strings/comments have no special meaning.

The scanner canonicalizes the Arabic aliases in the README. Additional accepted forms are `اذا` for `itha`, `والا` for `willa`, and `او` for `aw`. `بداية` canonicalizes to the entry-point name `bidaya`. Other identifiers keep their original spelling. Column positions count Unicode code points, not UTF-8 bytes or display cells. Terminal bidi handling and tabs may affect the visual placement of carets on Arabic/mixed lines.

## Scopes

Each block creates a lexical scope. Variables require initializers and cannot be read before declaration. Re-declaration in the same scope is an error, while an inner block may shadow an outer variable. The initializer resolves before introducing the new binding, so `{ khalli x: raqm = x + 1; }` can read an outer `x`. Assignment resolves the nearest enclosing declaration.

Parameters live in the function body's outer scope; a local in that same body cannot duplicate a parameter. Calls have independent frames and cannot access the caller's variables. Function and parameter types are fixed at compilation.

## Output and limits

`itba(value)` prints one value followed by a newline. Booleans print as `sah`/`khata`; numbers use Python's standard textual representation; strings retain Unicode text. There is no input or file/network access primitive.

CLI execution defaults to 1,000,000 instructions and 1,024 call frames, adjustable through `--max-steps` and `--max-frames`. These budgets apply to VM execution, not compilation or allocation. Huge integers, huge strings, deeply nested source, and artifacts can consume host resources; the tool is not a hostile-code sandbox.
