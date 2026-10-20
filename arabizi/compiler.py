"""Typed AST → symbolic stack IR → assembled bytecode with source maps."""
from dataclasses import asdict, dataclass, field
import json
import math
from typing import Any, List
from .lexer import lex
from .parser import Parser
from .semantic import Analyzer
from .model import ArabiziError, Span, binary


@dataclass
class Instruction:
    op: str
    arg: Any
    span: Span


@dataclass
class Function:
    name: str
    arity: int
    slots: int
    code: List[Instruction] = field(default_factory=list)


@dataclass
class Program:
    functions: dict
    source: str
    filename: str
    ir: dict = field(default_factory=dict)

    def dumps(self):
        return json.dumps({"format": "arabizi-bytecode", "version": 1,
                           "source": self.source, "filename": self.filename,
                           "functions": {k: asdict(v) for k, v in self.functions.items()}},
                          ensure_ascii=False, indent=2, allow_nan=False)

    def listing(self, symbolic=False):
        lines = []
        for name, fn in self.functions.items():
            lines.append(f"dallah {name} / {fn.arity} arguments / {fn.slots} slots")
            for i, ins in enumerate(self.ir[name] if symbolic else fn.code):
                arg = "" if ins.arg is None else json.dumps(ins.arg, ensure_ascii=False)
                lines.append(f"  {i:04d}  {ins.op:<10} {arg:<24} ; {ins.span.line}:{ins.span.column}")
        return "\n".join(lines)


class Emitter:
    def __init__(self, optimize):
        self.optimize, self.counter, self.code = optimize, 0, []

    def emit(self, op, arg, node):
        self.code.append(Instruction(op, arg, node.span))

    def label(self):
        self.counter += 1
        return f"L{self.counter}"

    def constant(self, n):
        if n.kind == "literal": return True, n.value
        if n.kind == "unary":
            ok, value = self.constant(n.children[0])
            if ok: return True, -value if n.value == "-" else not value
        if n.kind == "binary":
            a_ok, a = self.constant(n.children[0])
            if a_ok and n.value == "wa" and not a: return True, False
            if a_ok and n.value == "aw" and a: return True, True
            b_ok, b = self.constant(n.children[1])
            if a_ok and b_ok:
                try:
                    value = (a and b) if n.value == "wa" else ((a or b) if n.value == "aw" else binary(n.value, a, b))
                    # Keep diagnostics at runtime for exceptional arithmetic.
                    if type(value) is float and not math.isfinite(value): return False, None
                    return True, value
                except (ArithmeticError, ValueError): pass
        return False, None

    def expression(self, n):
        if self.optimize:
            ok, value = self.constant(n)
            if ok:
                self.emit("CONST", value, n)
                return
        if n.kind == "literal": self.emit("CONST", n.value, n)
        elif n.kind == "name": self.emit("LOAD", n.slot, n)
        elif n.kind == "call":
            for arg in n.children: self.expression(arg)
            self.emit("CALL", [n.value, len(n.children)], n)
        elif n.kind == "unary":
            self.expression(n.children[0])
            self.emit("NEG" if n.value == "-" else "NOT", None, n)
        elif n.kind == "binary":
            if n.value in ("wa", "aw"):
                end = self.label()
                self.expression(n.children[0]); self.emit("DUP", None, n)
                self.emit("JZ" if n.value == "wa" else "JNZ", end, n)
                self.emit("POP", None, n); self.expression(n.children[1])
                self.emit("LABEL", end, n)
            else:
                for c in n.children: self.expression(c)
                self.emit("BINARY", n.value, n)

    def statement(self, n):
        k = n.kind
        if k == "block":
            for c in n.children: self.statement(c)
        elif k in ("let", "assign"):
            self.expression(n.children[0]); self.emit("STORE", n.slot, n)
        elif k in ("print", "expr"):
            self.expression(n.children[0]); self.emit("PRINT" if k == "print" else "POP", None, n)
        elif k == "return":
            if n.children: self.expression(n.children[0])
            else: self.emit("CONST", None, n)
            self.emit("RET", None, n)
        elif k == "if":
            other, end = self.label(), self.label()
            self.expression(n.children[0]); self.emit("JZ", other, n)
            self.statement(n.children[1]); self.emit("JMP", end, n)
            self.emit("LABEL", other, n)
            if len(n.children) == 3: self.statement(n.children[2])
            self.emit("LABEL", end, n)
        elif k == "while":
            start, end = self.label(), self.label()
            self.emit("LABEL", start, n)
            self.expression(n.children[0]); self.emit("JZ", end, n)
            self.statement(n.children[1]); self.emit("JMP", start, n)
            self.emit("LABEL", end, n)


def assemble(ir):
    labels, offset = {}, 0
    for ins in ir:
        if ins.op == "LABEL": labels[ins.arg] = offset
        else: offset += 1
    return [Instruction(i.op, labels[i.arg] if i.op in ("JMP", "JZ", "JNZ") else i.arg, i.span)
            for i in ir if i.op != "LABEL"]


def frontend(source):
    try:
        return Analyzer().analyze(Parser(lex(source)).parse())
    except RecursionError:
        raise ArabiziError("compile", "Source nesting exceeds compiler limit") from None


def compile_source(source, filename="<input>", optimize=True):
    tree = frontend(source)
    functions, ir = {}, {}
    try:
        for fn in tree.children:
            emitter = Emitter(optimize)
            emitter.statement(fn.children[-1])
            # An implicit void return also makes all end labels valid targets.
            emitter.emit("CONST", None, fn); emitter.emit("RET", None, fn)
            ir[fn.value] = emitter.code
            functions[fn.value] = Function(fn.value, len(fn.children)-1, fn.slot, assemble(emitter.code))
    except RecursionError:
        raise ArabiziError("compile", "Source nesting exceeds compiler limit") from None
    return Program(functions, source, filename, ir)
