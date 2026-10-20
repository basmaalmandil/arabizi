"""A deterministic tour of the actual pipeline. Run with python3 demo.py."""
from pathlib import Path
from arabizi import ArabiziError, VM, compile_source
from arabizi.bytecode import loads
from arabizi.compiler import frontend
from arabizi.lexer import lex

ROOT = Path(__file__).resolve().parent


def main():
    source = (ROOT/'examples/riyadh.az').read_text(encoding='utf-8')
    print('ARABIZI / عربيزي — compiler laboratory\n')
    print('01  SOURCE\n'+source)
    tokens = lex(source)
    print(f'02  LEXER / {len(tokens)-1} tokens')
    print(' '.join(t.kind for t in tokens[:24])+' …\n')
    tree = frontend(source)
    print('03  TYPED AST / symbol resolution')
    for fn in tree.children:
        params = ', '.join(f'{p.value}: {p.type}@slot{p.slot}' for p in fn.children[:-1])
        print(f'    {fn.value}({params}) -> {fn.type}; {fn.slot} local slots')
    program = compile_source(source, 'examples/riyadh.az')
    print('\n04  SYMBOLIC IR\n'+program.listing(symbolic=True))
    print('\n05  ASSEMBLED BYTECODE\n'+program.listing())
    print('\n06  SERIALIZE → LOAD → VERIFY → EXECUTE')
    loaded = loads(program.dumps())
    machine = VM(loaded)
    machine.run()
    print(f'    Executed {machine.steps} instructions.\n')
    print('07  SOURCE-AWARE DIAGNOSTICS')
    for filename in ('type_error.az', 'runtime_error.az'):
        bad = (ROOT/'examples'/filename).read_text(encoding='utf-8')
        try: VM(compile_source(bad)).run()
        except ArabiziError as error: print(error.render(bad, 'examples/'+filename)+'\n')


if __name__ == '__main__': main()
