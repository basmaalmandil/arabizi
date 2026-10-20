"""Iterative stack VM: each call owns local slots and an operand stack."""
from dataclasses import dataclass, field
import math
from .model import ArabiziError, binary, display


@dataclass
class Frame:
    function: object
    locals: list
    ip: int = 0
    stack: list = field(default_factory=list)


class VM:
    def __init__(self, program, output=print, max_steps=1_000_000, max_frames=1024, trace=None):
        self.program, self.output, self.trace = program, output, trace
        self.max_steps, self.max_frames, self.steps = max_steps, max_frames, 0

    def run(self):
        entry = self.program.functions["bidaya"]
        frames = [Frame(entry, [None] * entry.slots)]
        self.steps = 0
        while frames:
            f = frames[-1]
            ins = f.function.code[f.ip]
            if self.steps >= self.max_steps:
                raise ArabiziError("runtime", f"Instruction budget exceeded ({self.max_steps})", ins.span)
            self.steps += 1
            if self.trace:
                self.trace(f"{f.function.name}:{f.ip:04d} {ins.op} {ins.arg!r} stack={f.stack!r}")
            f.ip += 1
            s, op, arg = f.stack, ins.op, ins.arg
            try:
                if op == "CONST": s.append(arg)
                elif op == "LOAD": s.append(f.locals[arg])
                elif op == "STORE": f.locals[arg] = s.pop()
                elif op == "POP": s.pop()
                elif op == "DUP": s.append(s[-1])
                elif op == "NEG": s.append(-s.pop())
                elif op == "NOT": s.append(not s.pop())
                elif op == "BINARY":
                    b, a = s.pop(), s.pop()
                    result = binary(arg, a, b)
                    if type(result) is float and not math.isfinite(result):
                        raise ArithmeticError("Non-finite floating-point result")
                    s.append(result)
                elif op == "PRINT": self.output(display(s.pop()))
                elif op == "JMP": f.ip = arg
                elif op in ("JZ", "JNZ"):
                    value = s.pop()
                    if (op == "JZ" and not value) or (op == "JNZ" and value): f.ip = arg
                elif op == "CALL":
                    name, argc = arg
                    if len(frames) >= self.max_frames:
                        raise ArabiziError("runtime", f"Call depth exceeded ({self.max_frames})", ins.span)
                    fn = self.program.functions[name]
                    args = s[-argc:] if argc else []
                    if argc: del s[-argc:]
                    frames.append(Frame(fn, args + [None] * (fn.slots - argc)))
                elif op == "RET":
                    result = s.pop()
                    frames.pop()
                    if frames: frames[-1].stack.append(result)
                    else: return result
                else: raise ArabiziError("runtime", f"Unknown opcode {op}", ins.span)
            except ZeroDivisionError:
                raise ArabiziError("runtime", "Division by zero", ins.span) from None
            except ArithmeticError as exc:
                raise ArabiziError("runtime", str(exc), ins.span) from None
            except (TypeError, ValueError) as exc:
                raise ArabiziError("runtime", f"Invalid bytecode operand: {exc}", ins.span) from None
