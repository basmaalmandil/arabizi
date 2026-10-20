"""Single-pass scanner; longest-match operators and Unicode identifiers."""
import math
from .model import ArabiziError, Span, Token

ALIASES = {
    "دالة": "dallah", "متغير": "khalli", "اذا": "itha", "إذا": "itha",
    "والا": "willa", "وإلا": "willa", "طالما": "talama", "ارجع": "arja",
    "اطبع": "itba", "رقم": "raqm", "كسر": "kasr", "نص": "nass",
    "منطق": "mantiq", "فراغ": "faragh", "صح": "sah", "خطأ": "khata",
    "و": "wa", "او": "aw", "أو": "aw", "ليس": "mish", "بداية": "bidaya",
}
KEYWORDS = set(ALIASES.values()) - {"bidaya"}


def lex(source):
    tokens = []
    i, line, col = 0, 1, 1

    def advance():
        nonlocal i, line, col
        c = source[i]
        i += 1
        if c == "\n": line, col = line + 1, 1
        else: col += 1
        return c

    def fail(message, span):
        raise ArabiziError("lex", message, span)

    while i < len(source):
        c = source[i]
        if c.isspace():
            advance()
            continue
        start, span = i, Span(line, col)
        if source.startswith("//", i):
            while i < len(source) and source[i] != "\n": advance()
            continue
        if source.startswith("/*", i):
            advance(); advance()
            depth = 1
            while i < len(source) and depth:
                if source.startswith("/*", i):
                    advance(); advance(); depth += 1
                elif source.startswith("*/", i):
                    advance(); advance(); depth -= 1
                else: advance()
            if depth: fail("Unterminated block comment", span)
            continue
        if c == '"':
            advance()
            value = ""
            while i < len(source) and source[i] != '"':
                if source[i] == "\n": fail("Newline in string; use \\n", span)
                ch = advance()
                if ch == "\\":
                    if i == len(source): fail("Unterminated string", span)
                    esc = advance()
                    escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                    if esc not in escapes: fail(f"Unknown escape \\{esc}", span)
                    ch = escapes[esc]
                value += ch
            if i == len(source): fail("Unterminated string", span)
            advance()
            tokens.append(Token("STRING", value, Span(span.line, span.column, i-start)))
            continue
        if c.isdecimal():
            while i < len(source) and source[i].isdecimal(): advance()
            if i < len(source) and source[i] == ".":
                advance()
                if i == len(source) or not source[i].isdecimal(): fail("Expected digits after decimal point", span)
                while i < len(source) and source[i].isdecimal(): advance()
            raw = source[start:i]
            try: value = float(raw) if "." in raw else int(raw)
            except ValueError: fail("Invalid or excessively long number", span)
            if type(value) is float and not math.isfinite(value):
                fail("Floating literal is out of range", span)
            tokens.append(Token("NUMBER", value, Span(span.line, span.column, i-start)))
            continue
        if c == "_" or c.isalpha():
            advance()
            while i < len(source) and (source[i].isalnum() or source[i] == "_"): advance()
            word = ALIASES.get(source[start:i], source[start:i])
            tokens.append(Token(word if word in KEYWORDS else "ID", word, Span(span.line, span.column, i-start)))
            continue
        pair = source[i:i+2]
        if pair in ("->", "==", "!=", "<=", ">="):
            advance(); advance()
            tokens.append(Token(pair, pair, Span(span.line, span.column, 2)))
        elif c in "+-*/%=<>!(){}:,;":
            advance()
            tokens.append(Token(c, c, span))
        else:
            fail(f"Unexpected character {c!r}", span)
    tokens.append(Token("EOF", None, Span(line, col)))
    return tokens
