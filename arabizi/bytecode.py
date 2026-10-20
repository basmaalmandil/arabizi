"""Versioned artifact reader and control-flow/stack verifier."""
import json
import math
from .compiler import Program, Function, Instruction
from .model import ArabiziError, Span

NO_ARG = {"POP", "DUP", "NEG", "NOT", "PRINT", "RET"}
JUMPS = {"JMP", "JZ", "JNZ"}
OPS = NO_ARG | JUMPS | {"CONST", "LOAD", "STORE", "BINARY", "CALL"}


def invalid(message):
    raise ArabiziError("bytecode", message)


def integer(value, low=0):
    return type(value) is int and value >= low


def loads(text):
    try:
        data = json.loads(text)
        if (not isinstance(data, dict) or data.get("format") != "arabizi-bytecode"
                or type(data.get("version")) is not int or data["version"] != 1):
            invalid("Unsupported artifact format/version")
        if not isinstance(data.get("source"), str) or not isinstance(data.get("filename"), str):
            invalid("Missing source metadata")
        raw = data.get("functions")
        if not isinstance(raw, dict) or "bidaya" not in raw: invalid("Missing bidaya function")
        functions = {}
        for name, item in raw.items():
            if not isinstance(item, dict) or item.get("name") != name: invalid("Invalid function metadata")
            arity, slots = item.get("arity"), item.get("slots")
            if not integer(arity) or not integer(slots) or not arity <= slots <= 65536:
                invalid("Invalid frame size")
            if not isinstance(item.get("code"), list) or not item["code"]: invalid("Empty function")
            code = []
            for ins in item["code"]:
                if not isinstance(ins, dict) or not isinstance(ins.get("op"), str) or ins["op"] not in OPS:
                    invalid("Unknown opcode")
                span = ins.get("span")
                if not isinstance(span, dict) or any(not integer(span.get(k), 1) for k in ("line", "column", "length")):
                    invalid("Invalid source span")
                code.append(Instruction(ins["op"], ins.get("arg"), Span(**span)))
            functions[name] = Function(name, arity, slots, code)
        if functions["bidaya"].arity != 0: invalid("bidaya must take no arguments")
        program = Program(functions, data["source"], data["filename"])
        verify(program)
        return program
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise ArabiziError("bytecode", f"Malformed artifact: {exc}") from None


def verify(program):
    for fn in program.functions.values():
        for ins in fn.code:
            op, arg = ins.op, ins.arg
            if op in NO_ARG and arg is not None: invalid(f"{op} takes no operand")
            if op in JUMPS and (not integer(arg) or arg >= len(fn.code)): invalid("Invalid jump target")
            if op in ("LOAD", "STORE") and (not integer(arg) or arg >= fn.slots): invalid("Invalid local slot")
            if op == "CONST" and (type(arg) not in (str, int, float, bool, type(None)) or
                                  (type(arg) is float and not math.isfinite(arg))): invalid("Invalid constant")
            if op == "BINARY" and (not isinstance(arg, str) or arg not in {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="}):
                invalid("Invalid binary operator")
            if op == "CALL":
                if (not isinstance(arg, list) or len(arg) != 2 or not isinstance(arg[0], str)
                        or arg[0] not in program.functions or not integer(arg[1])
                        or arg[1] != program.functions[arg[0]].arity): invalid("Invalid call signature")
        # Fixed point over reachable PCs: stack height must agree at joins;
        # definitely initialized local slots are intersected across incoming edges.
        states, pending = {}, [(0, 0, frozenset(range(fn.arity)))]
        while pending:
            pc, height, initialized = pending.pop()
            if not 0 <= pc < len(fn.code): invalid("Control flow falls off function")
            if pc in states:
                old_height, old_init = states[pc]
                if height != old_height: invalid("Inconsistent stack height at branch")
                merged = initialized & old_init
                if merged == old_init: continue
                initialized = merged
            states[pc] = height, initialized
            ins = fn.code[pc]
            op, arg = ins.op, ins.arg
            need, delta = 0, 0
            if op in ("CONST", "LOAD"): delta = 1
            elif op == "DUP": need, delta = 1, 1
            elif op in ("POP", "STORE", "PRINT", "JZ", "JNZ", "RET"): need, delta = 1, -1
            elif op in ("NEG", "NOT"): need = 1
            elif op == "BINARY": need, delta = 2, -1
            elif op == "CALL": need, delta = arg[1], 1-arg[1]
            if height < need: invalid("Operand stack underflow")
            if op == "LOAD" and arg not in initialized: invalid("Read of uninitialized local slot")
            if op == "STORE": initialized = initialized | {arg}
            if op == "RET":
                if height != 1: invalid("Return must have exactly one stack value")
                continue
            successors = [arg] if op == "JMP" else ([arg, pc+1] if op in ("JZ", "JNZ") else [pc+1])
            pending.extend((target, height+delta, frozenset(initialized)) for target in successors)
