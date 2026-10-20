import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from .compiler import compile_source, frontend
from .bytecode import loads
from .lexer import lex
from .model import ArabiziError
from .vm import VM


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arabizi", description="Compile, inspect, and run Arabizi programs")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "check", "compile", "tokens", "ast", "ir", "disasm"):
        cmd = sub.add_parser(command)
        cmd.add_argument("file", type=Path)
        cmd.add_argument("--no-opt", action="store_true", help="Disable constant folding")
        if command == "compile": cmd.add_argument("-o", "--output", required=True, type=Path)
        if command == "run":
            cmd.add_argument("--trace", action="store_true")
            cmd.add_argument("--max-steps", type=int, default=1_000_000)
            cmd.add_argument("--max-frames", type=int, default=1024)
    args = parser.parse_args(argv)
    source, filename = "", str(args.file)
    try:
        source = args.file.read_text(encoding="utf-8")
        if args.command == "tokens":
            print(json.dumps([asdict(t) for t in lex(source)], ensure_ascii=False, indent=2))
        elif args.command == "ast":
            print(json.dumps(asdict(frontend(source)), ensure_ascii=False, indent=2))
        else:
            if args.file.suffix == ".azbc":
                if args.command not in ("run", "disasm"):
                    raise ArabiziError("cli", "Bytecode supports only run and disasm")
                program = loads(source)
                source, filename = program.source, program.filename
            else: program = compile_source(source, filename, not args.no_opt)
            if args.command == "run":
                if args.max_steps < 1 or args.max_frames < 1:
                    raise ArabiziError("cli", "Execution limits must be positive")
                VM(program, max_steps=args.max_steps, max_frames=args.max_frames,
                   trace=(lambda s: print(s, file=sys.stderr)) if args.trace else None).run()
            elif args.command == "compile":
                args.output.write_text(program.dumps() + "\n", encoding="utf-8")
                print(f"Compiled {len(program.functions)} functions → {args.output}")
            elif args.command == "check": print("OK: syntax and types verified")
            else: print(program.listing(symbolic=args.command == "ir"))
        return 0
    except ArabiziError as exc:
        print(exc.render(source, filename), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"arabizi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
