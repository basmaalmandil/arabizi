"""Independent tree-walking execution baseline for differential testing.

Shares the checked AST and primitive arithmetic semantics, but does not emit or
execute bytecode. Variable access walks lexical dictionaries instead of VM slots.
"""
import math
from .model import ArabiziError, binary, display


class Returned(Exception):
    def __init__(self, value): self.value = value


class Interpreter:
    def __init__(self, tree, output=print):
        self.functions = {n.value: n for n in tree.children}
        self.output = output
        self.scopes = []

    def run(self): return self.call("bidaya", [])

    def call(self, name, args):
        fn = self.functions[name]
        previous = self.scopes
        self.scopes = [dict(zip([p.value for p in fn.children[:-1]], args))]
        try: self.block(fn.children[-1])
        except Returned as result: return result.value
        finally: self.scopes = previous

    def scope(self, name):
        return next(s for s in reversed(self.scopes) if name in s)

    def block(self, n):
        self.scopes.append({})
        try:
            for child in n.children: self.statement(child)
        finally: self.scopes.pop()

    def statement(self, n):
        k = n.kind
        if k == "block": self.block(n)
        elif k == "let": self.scopes[-1][n.value] = self.expression(n.children[0])
        elif k == "assign": self.scope(n.value)[n.value] = self.expression(n.children[0])
        elif k == "return": raise Returned(self.expression(n.children[0]) if n.children else None)
        elif k == "print": self.output(display(self.expression(n.children[0])))
        elif k == "expr": self.expression(n.children[0])
        elif k == "if":
            if self.expression(n.children[0]): self.block(n.children[1])
            elif len(n.children) == 3: self.block(n.children[2])
        elif k == "while":
            while self.expression(n.children[0]): self.block(n.children[1])

    def expression(self, n):
        if n.kind == "literal": return n.value
        if n.kind == "name": return self.scope(n.value)[n.value]
        if n.kind == "call": return self.call(n.value, [self.expression(c) for c in n.children])
        if n.kind == "unary":
            value = self.expression(n.children[0])
            return -value if n.value == "-" else not value
        a = self.expression(n.children[0])
        if n.value == "wa": return a and self.expression(n.children[1])
        if n.value == "aw": return a or self.expression(n.children[1])
        b = self.expression(n.children[1])
        try:
            result = binary(n.value, a, b)
            if type(result) is float and not math.isfinite(result): raise ArithmeticError("Non-finite floating-point result")
            return result
        except ZeroDivisionError: raise ArabiziError("runtime", "Division by zero", n.span) from None
        except ArithmeticError as exc: raise ArabiziError("runtime", str(exc), n.span) from None
