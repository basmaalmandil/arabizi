"""Two-pass function resolution, lexical scopes, static types, and return analysis."""
from .model import ArabiziError, value_type


class Analyzer:
    def error(self, node, message):
        raise ArabiziError("type", message, node.span)

    def require(self, node, actual, expected):
        if actual != expected:
            self.error(node, f"Expected {expected}, got {actual}")

    def analyze(self, tree):
        self.functions = {}
        for fn in tree.children:
            if fn.value in self.functions: self.error(fn, f"Duplicate function '{fn.value}'")
            self.functions[fn.value] = fn
        if "bidaya" not in self.functions:
            self.error(tree, "Missing entry point: dallah bidaya() -> faragh { ... }")
        entry = self.functions["bidaya"]
        if len(entry.children) != 1 or entry.type != "faragh":
            self.error(entry, "bidaya must take no arguments and return faragh")
        for fn in tree.children:
            self.scopes, self.next_slot, self.result_type = [{}], 0, fn.type
            for param in fn.children[:-1]: self.declare(param)
            returns = self.block(fn.children[-1], new_scope=False)
            if fn.type != "faragh" and not returns:
                self.error(fn, f"Function '{fn.value}' must return {fn.type} on every path")
            fn.slot = self.next_slot  # Frame size, not a variable slot.
        return tree

    def declare(self, node):
        if node.type == "faragh": self.error(node, "Variables and parameters cannot have type faragh")
        if node.value in self.scopes[-1]: self.error(node, f"Duplicate declaration '{node.value}'")
        node.slot = self.next_slot
        self.next_slot += 1
        self.scopes[-1][node.value] = (node.type, node.slot)

    def lookup(self, node):
        for scope in reversed(self.scopes):
            if node.value in scope:
                typ, node.slot = scope[node.value]
                return typ
        self.error(node, f"Unknown variable '{node.value}'")

    def block(self, node, new_scope=True):
        if new_scope: self.scopes.append({})
        returns = False
        for stmt in node.children:
            if returns: self.error(stmt, "Unreachable statement after guaranteed return")
            returns = self.statement(stmt)
        if new_scope: self.scopes.pop()
        return returns

    def statement(self, n):
        k = n.kind
        if k == "block": return self.block(n)
        if k == "let":
            self.require(n, self.expression(n.children[0]), n.type)
            self.declare(n)
        elif k == "assign":
            self.require(n, self.expression(n.children[0]), self.lookup(n))
        elif k == "return":
            typ = self.expression(n.children[0]) if n.children else "faragh"
            self.require(n, typ, self.result_type)
            return True
        elif k in ("if", "while"):
            self.require(n.children[0], self.expression(n.children[0]), "mantiq")
            first = self.block(n.children[1])
            second = self.block(n.children[2]) if len(n.children) == 3 else False
            return k == "if" and first and second
        elif k in ("print", "expr"):
            typ = self.expression(n.children[0])
            if k == "print" and typ == "faragh": self.error(n, "Cannot print a faragh value")
        return False

    def expression(self, n):
        if n.kind == "literal": n.type = value_type(n.value)
        elif n.kind == "name": n.type = self.lookup(n)
        elif n.kind == "call":
            fn = self.functions.get(n.value)
            if fn is None: self.error(n, f"Unknown function '{n.value}'")
            params = fn.children[:-1]
            if len(params) != len(n.children):
                self.error(n, f"'{n.value}' expects {len(params)} arguments, got {len(n.children)}")
            for arg, param in zip(n.children, params):
                self.require(arg, self.expression(arg), param.type)
            n.type = fn.type
        elif n.kind == "unary":
            typ = self.expression(n.children[0])
            if n.value == "-":
                if typ not in ("raqm", "kasr"): self.error(n, "Unary '-' needs a number")
            else: self.require(n, typ, "mantiq")
            n.type = typ
        elif n.kind == "binary":
            a, b = [self.expression(c) for c in n.children]
            self.require(n, b, a)
            op = n.value
            if op in ("wa", "aw"):
                self.require(n, a, "mantiq"); n.type = "mantiq"
            elif op in ("==", "!="):
                if a == "faragh": self.error(n, "Cannot compare faragh values")
                n.type = "mantiq"
            elif op in ("<", "<=", ">", ">="):
                if a not in ("raqm", "kasr"): self.error(n, "Ordering needs numeric operands")
                n.type = "mantiq"
            else:
                allowed = ("raqm",) if op == "%" else ("raqm", "kasr")
                if op == "+": allowed += ("nass",)
                if a not in allowed: self.error(n, f"Operator '{op}' does not support {a}")
                n.type = a
        return n.type
