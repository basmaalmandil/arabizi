"""Recursive-descent statements and precedence-climbing expressions."""
from .model import ArabiziError, Node

TYPES = {"raqm", "kasr", "nass", "mantiq", "faragh"}
PRECEDENCE = {"aw": 1, "wa": 2, "==": 3, "!=": 3, "<": 4, "<=": 4,
              ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6, "%": 6}


class Parser:
    def __init__(self, tokens):
        self.tokens, self.i = tokens, 0

    @property
    def current(self): return self.tokens[self.i]

    def take(self, kind=None):
        token = self.current
        if kind and token.kind != kind:
            raise ArabiziError("parse", f"Expected {kind!r}, found {token.kind!r}", token.span)
        self.i += 1
        return token

    def match(self, kind):
        if self.current.kind == kind:
            return self.take()
        return None

    def typename(self):
        if self.current.kind not in TYPES:
            raise ArabiziError("parse", "Expected a type: raqm, kasr, nass, mantiq, or faragh", self.current.span)
        return self.take().kind

    def parse(self):
        result = Node("program", self.current.span)
        while self.current.kind != "EOF":
            start = self.take("dallah")
            name = self.take("ID").value
            self.take("(")
            params = []
            if self.current.kind != ")":
                while True:
                    p = self.take("ID")
                    self.take(":")
                    params.append(Node("param", p.span, p.value, type=self.typename()))
                    if not self.match(","): break
            self.take(")"); self.take("->")
            typ = self.typename()
            result.children.append(Node("function", start.span, name, params + [self.block()], typ))
        return result

    def block(self):
        t = self.take("{")
        node = Node("block", t.span)
        while self.current.kind not in ("}", "EOF"):
            node.children.append(self.statement())
        self.take("}")
        return node

    def statement(self):
        t = self.current
        if t.kind == "{": return self.block()
        if self.match("khalli"):
            name = self.take("ID").value
            self.take(":")
            typ = self.typename()
            self.take("=")
            node = Node("let", t.span, name, [self.expression()], typ)
        elif self.match("itha"):
            self.take("("); cond = self.expression(); self.take(")")
            children = [cond, self.block()]
            if self.match("willa"): children.append(self.block())
            return Node("if", t.span, children=children)
        elif self.match("talama"):
            self.take("("); cond = self.expression(); self.take(")")
            return Node("while", t.span, children=[cond, self.block()])
        elif self.match("arja"):
            node = Node("return", t.span, children=[] if self.current.kind == ";" else [self.expression()])
        elif self.match("itba"):
            self.take("("); expr = self.expression(); self.take(")")
            node = Node("print", t.span, children=[expr])
        elif t.kind == "ID" and self.tokens[self.i+1].kind == "=":
            name = self.take().value; self.take("=")
            node = Node("assign", t.span, name, [self.expression()])
        else:
            node = Node("expr", t.span, children=[self.expression()])
        self.take(";")
        return node

    def expression(self, minimum=1):
        t = self.take()
        if t.kind in ("-", "!", "mish"):
            left = Node("unary", t.span, t.kind, [self.expression(7)])
        elif t.kind == "(":
            left = self.expression(); self.take(")")
        elif t.kind in ("NUMBER", "STRING", "sah", "khata"):
            value = t.value if t.kind not in ("sah", "khata") else t.kind == "sah"
            left = Node("literal", t.span, value)
        elif t.kind == "ID":
            left = Node("name", t.span, t.value)
            if self.match("("):
                left.kind = "call"
                if self.current.kind != ")":
                    while True:
                        left.children.append(self.expression())
                        if not self.match(","): break
                self.take(")")
        else:
            raise ArabiziError("parse", f"Expected expression, found {t.kind!r}", t.span)
        while PRECEDENCE.get(self.current.kind, 0) >= minimum:
            op = self.take()
            right = self.expression(PRECEDENCE[op.kind] + 1)
            left = Node("binary", op.span, op.kind, [left, right])
        return left
