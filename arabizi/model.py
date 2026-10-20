"""Shared syntax and source-aware diagnostics."""
from dataclasses import dataclass, field
from typing import Any, List


@dataclass(frozen=True)
class Span:
    line: int
    column: int
    length: int = 1


class ArabiziError(Exception):
    def __init__(self, phase, message, span=None):
        self.phase, self.message, self.span = phase, message, span
        super().__init__(message)

    def render(self, source, filename="<input>"):
        if self.span is None:
            return f"{filename}: {self.phase}: {self.message}"
        s = self.span
        lines = source.splitlines()
        line = lines[s.line - 1] if s.line <= len(lines) else ""
        return (f"{filename}:{s.line}:{s.column}: {self.phase}: {self.message}\n"
                f"  {line}\n  {' ' * (s.column - 1)}{'^' * max(1, s.length)}")


@dataclass
class Token:
    kind: str
    value: Any
    span: Span


@dataclass
class Node:
    kind: str
    span: Span
    value: Any = None
    children: List["Node"] = field(default_factory=list)
    type: str = ""
    slot: int = -1


def value_type(value):
    return {bool: "mantiq", int: "raqm", float: "kasr", str: "nass", type(None): "faragh"}[type(value)]


def display(value):
    if type(value) is bool:
        return "sah" if value else "khata"
    return str(value)


def binary(op, a, b):
    # Integer division truncates toward zero, without converting large ints to float.
    if op == "/" and type(a) is int:
        q = abs(a) // abs(b)
        return -q if (a < 0) != (b < 0) else q
    if op == "%":
        return a - binary("/", a, b) * b
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op == "/": return a / b
    if op == "==": return a == b
    if op == "!=": return a != b
    if op == "<": return a < b
    if op == "<=": return a <= b
    if op == ">": return a > b
    if op == ">=": return a >= b
    raise ValueError(f"Unknown operator {op}")
