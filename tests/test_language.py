import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

from arabizi import ArabiziError, VM, compile_source
from arabizi.bytecode import loads, verify
from arabizi.compiler import frontend
from arabizi.interpreter import Interpreter
from arabizi.lexer import lex

ROOT = Path(__file__).resolve().parents[1]


def wrap(body): return "dallah bidaya() -> faragh { " + body + " }"


class ExecutionTests(unittest.TestCase):
    def execute(self, source, expected):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                program = compile_source(source, optimize=optimized)
                verify(program)
                out = []
                VM(program, output=out.append).run()
                self.assertEqual(out, expected)
                restored = loads(program.dumps())
                out = []
                VM(restored, output=out.append).run()
                self.assertEqual(out, expected)
        out = []
        Interpreter(frontend(source), output=out.append).run()
        self.assertEqual(out, expected)

    def test_precedence_and_associativity(self):
        self.execute(wrap('itba(2+3*4); itba(20-5-3); itba((2+3)*4);'), ['14', '12', '20'])

    def test_integer_division_and_remainder(self):
        self.execute(wrap('itba(-7/3); itba(-7%3); itba(7/-3); itba(7%-3);'), ['-2', '-1', '-2', '1'])

    def test_large_integers(self):
        self.execute(wrap('itba(999999999999999999999999999999 / 3);'), ['333333333333333333333333333333'])

    def test_float(self):
        self.execute(wrap('khalli x: kasr = 7.5; itba(x/2.5); itba(-x);'), ['3.0', '-7.5'])

    def test_strings_and_escapes(self):
        self.execute(wrap('itba("أهلاً" + " Riyadh"); itba("a\\n\\t\\\"\\\\");'), ['أهلاً Riyadh', 'a\n\t"\\'])

    def test_booleans(self):
        self.execute(wrap('itba(mish khata wa sah aw khata); itba(!sah); itba(2!=3);'), ['sah', 'khata', 'sah'])

    def test_short_circuit_side_effects(self):
        self.execute('dallah side() -> mantiq { itba("called"); arja sah; }' + wrap(
            'itba(khata wa side()); itba(sah aw side()); itba(sah wa side());'),
            ['khata', 'sah', 'called', 'sah'])

    def test_short_circuit_division(self):
        self.execute(wrap('itba(khata wa (1/0==1)); itba(sah aw (1/0==1));'), ['khata', 'sah'])

    def test_argument_evaluation_order(self):
        self.execute('dallah say(x: raqm) -> raqm { itba(x); arja x; } '
                     'dallah sum(a: raqm, b: raqm) -> raqm { arja a+b; }' +
                     wrap('itba(sum(say(1), say(2)));'), ['1', '2', '3'])

    def test_shadowing(self):
        self.execute(wrap('khalli x: raqm=3; { khalli x: raqm=x+1; x=x+1; itba(x); } itba(x);'), ['5', '3'])

    def test_loop_local_initialization(self):
        self.execute(wrap('khalli i: raqm=0; talama(i<3) { khalli x: raqm=i; itba(x); i=i+1; }'), ['0', '1', '2'])

    def test_nested_loops(self):
        self.execute(wrap('khalli i: raqm=0; khalli sum: raqm=0; talama(i<4) { '
                     'khalli j: raqm=0; talama(j<i) { sum=sum+1; j=j+1; } i=i+1; } itba(sum);'), ['6'])

    def test_return_from_loop(self):
        self.execute('dallah f() -> raqm { talama(sah) { arja 7; } arja 9; }' + wrap('itba(f());'), ['7'])

    def test_mutual_recursion_forward_references(self):
        self.execute('dallah even(n: raqm) -> mantiq { itha(n==0) { arja sah; } willa { arja odd(n-1); } } '
                     'dallah odd(n: raqm) -> mantiq { itha(n==0) { arja khata; } willa { arja even(n-1); } } '
                     + wrap('itba(even(10)); itba(odd(10));'), ['sah', 'khata'])

    def test_void_calls(self):
        self.execute('dallah f() -> faragh { itba("ok"); arja; }' + wrap('f();'), ['ok'])

    def test_comments(self):
        self.execute(wrap('/* outer /* inner */ done */ itba(7); // tail\n'), ['7'])

    def test_arabic_example(self):
        self.execute((ROOT/'examples/arabic.az').read_text(), ['مجموع الأعداد من ١ إلى ١٠', '55'])

    def test_riyadh_example(self):
        self.execute((ROOT/'examples/riyadh.az').read_text(),
                     ['أهلاً بالرياض — Arabizi transit demo', '6', '8', '10', '8', '9', 'Total illustrative fare (SAR):', '41'])

    def test_recursive_factorial(self):
        self.execute((ROOT/'examples/factorial.az').read_text(), ['10! =', '3628800'])

    def test_optimizer_reduces_steps(self):
        src = wrap('khalli i: raqm=0; talama(i<10) { itba((2+3)*4); i=i+1; }')
        a, b = [VM(compile_source(src, optimize=opt), output=lambda s: None) for opt in (False, True)]
        a.run(); b.run()
        self.assertLess(b.steps, a.steps)

    def test_deterministic_generated_arithmetic(self):
        rng = random.Random(2030)
        def expr(depth):
            if depth == 0:
                n = rng.randint(-20, 20)
                return str(n), n
            a, av = expr(depth-1); b, bv = expr(depth-1)
            op = rng.choice(['+', '-', '*'])
            expected = {'+': lambda: av+bv, '-': lambda: av-bv, '*': lambda: av*bv}[op]()
            return f'({a} {op} {b})', expected
        for _ in range(100):
            text, expected = expr(3)
            with self.subTest(expression=text): self.execute(wrap(f'itba({text});'), [str(expected)])

    def test_generated_loop_checksums(self):
        for n in range(20):
            self.execute(wrap(f'khalli i: raqm=0; khalli s: raqm=0; talama(i<{n}) '
                              '{ s=s+i*i; i=i+1; } itba(s);'), [str(sum(i*i for i in range(n)))])


class DiagnosticTests(unittest.TestCase):
    def rejects(self, source, fragment):
        with self.assertRaises(ArabiziError) as caught: compile_source(source)
        self.assertIn(fragment, str(caught.exception))
        return caught.exception

    def test_unknown_variable(self): self.rejects(wrap('itba(missing);'), 'Unknown variable')
    def test_unknown_function(self): self.rejects(wrap('missing();'), 'Unknown function')
    def test_duplicate_variable(self): self.rejects(wrap('khalli x: raqm=1; khalli x: raqm=2;'), 'Duplicate declaration')
    def test_duplicate_parameter(self): self.rejects('dallah f(x: raqm, x: raqm) -> faragh {}'+wrap(''), 'Duplicate declaration')
    def test_duplicate_function(self): self.rejects(wrap('')+wrap(''), 'Duplicate function')
    def test_wrong_initializer(self): self.rejects(wrap('khalli x: raqm="a";'), 'Expected raqm, got nass')
    def test_wrong_assignment(self): self.rejects(wrap('khalli x: raqm=1; x=sah;'), 'Expected raqm')
    def test_bool_is_not_int(self): self.rejects(wrap('itba(sah+1);'), 'Expected mantiq')
    def test_no_implicit_float_conversion(self): self.rejects(wrap('itba(1+2.0);'), 'Expected raqm')
    def test_condition_must_be_bool(self): self.rejects(wrap('itha(1) {}'), 'Expected mantiq')
    def test_loop_condition_must_be_bool(self): self.rejects(wrap('talama("yes") {}'), 'Expected mantiq')
    def test_wrong_argument(self): self.rejects('dallah f(x: raqm)->faragh {}'+wrap('f(sah);'), 'Expected raqm')
    def test_wrong_arity(self): self.rejects('dallah f(x: raqm)->faragh {}'+wrap('f();'), 'expects 1 arguments')
    def test_missing_return(self): self.rejects('dallah f()->raqm { itha(sah) { arja 1; } }'+wrap(''), 'every path')
    def test_wrong_return(self): self.rejects('dallah f()->raqm { arja "x"; }'+wrap(''), 'Expected raqm')
    def test_void_variable(self): self.rejects('dallah f()->faragh {}'+wrap('khalli x: faragh=f();'), 'cannot have type faragh')
    def test_void_print(self): self.rejects('dallah f()->faragh {}'+wrap('itba(f());'), 'Cannot print')
    def test_void_compare(self): self.rejects('dallah f()->faragh {}'+wrap('itba(f()==f());'), 'Cannot compare')
    def test_out_of_scope(self): self.rejects(wrap('{ khalli x: raqm=1; } itba(x);'), 'Unknown variable')
    def test_self_initialization(self): self.rejects(wrap('khalli x: raqm=x;'), 'Unknown variable')
    def test_unreachable(self): self.rejects(wrap('arja; itba(1);'), 'Unreachable')
    def test_missing_entry(self): self.rejects('', 'Missing entry')
    def test_invalid_entry(self): self.rejects('dallah bidaya(x: raqm)->faragh {}', 'no arguments')
    def test_missing_semicolon(self): self.rejects(wrap('itba(1)'), "Expected ';'")
    def test_missing_brace(self): self.rejects('dallah bidaya()->faragh {', "Expected '}'")
    def test_unknown_character(self): self.rejects(wrap('@'), 'Unexpected character')
    def test_unterminated_string(self): self.rejects('dallah bidaya()->faragh { itba("', 'Unterminated string')
    def test_unterminated_comment(self): self.rejects('/*', 'Unterminated block comment')
    def test_invalid_escape(self): self.rejects(wrap('itba("\\q");'), 'Unknown escape')
    def test_malformed_decimal(self): self.rejects(wrap('itba(1.);'), 'Expected digits')
    def test_float_modulo(self): self.rejects(wrap('itba(2.0%1.0);'), 'does not support kasr')
    def test_unary_type(self): self.rejects(wrap('itba(-sah);'), 'needs a number')
    def test_deep_nesting(self): self.rejects(wrap('itba('+'('*2000+'1'+')'*2000+');'), 'nesting exceeds')

    def test_source_caret(self):
        source = 'dallah bidaya() -> faragh {\n  itba(missing);\n}'
        error = self.rejects(source, 'Unknown variable')
        self.assertEqual((error.span.line, error.span.column), (2, 8))
        self.assertIn('demo.az:2:8: type:', error.render(source, 'demo.az'))
        self.assertIn('^^^^^^^', error.render(source))

    def test_runtime_division_both_modes(self):
        for opt in (False, True):
            with self.assertRaisesRegex(ArabiziError, 'Division by zero'):
                VM(compile_source(wrap('itba(10/0);'), optimize=opt)).run()

    def test_instruction_budget(self):
        with self.assertRaisesRegex(ArabiziError, 'Instruction budget'):
            VM(compile_source(wrap('talama(sah) {}')), max_steps=50).run()

    def test_call_depth(self):
        source = 'dallah f()->faragh { f(); }'+wrap('f();')
        with self.assertRaisesRegex(ArabiziError, 'Call depth'):
            VM(compile_source(source), max_frames=20).run()

    def test_vm_recursion_does_not_use_python_stack(self):
        source = 'dallah f(n: raqm)->raqm { itha(n==0) { arja 0; } willa { arja f(n-1); } }'+wrap('itba(f(1500));')
        output = []
        VM(compile_source(source), output=output.append, max_frames=2000).run()
        self.assertEqual(output, ['0'])


class ArtifactTests(unittest.TestCase):
    def artifact(self): return json.loads(compile_source(wrap('itba(1);')).dumps())
    def reject(self, data, fragment):
        with self.assertRaisesRegex(ArabiziError, fragment): loads(json.dumps(data))

    def test_version(self):
        data = self.artifact(); data['version'] = 2; self.reject(data, 'version')
    def test_bad_json(self):
        with self.assertRaises(ArabiziError): loads('{')
    def test_opcode(self):
        data = self.artifact(); data['functions']['bidaya']['code'][0]['op'] = 'EXEC'; self.reject(data, 'opcode')
    def test_underflow(self):
        data = self.artifact(); data['functions']['bidaya']['code'][0].update(op='POP', arg=None); self.reject(data, 'underflow')
    def test_jump(self):
        data = self.artifact(); data['functions']['bidaya']['code'][0].update(op='JMP', arg=100); self.reject(data, 'jump target')
    def test_uninitialized_slot(self):
        data = self.artifact(); fn = data['functions']['bidaya']; fn['slots'] = 1
        fn['code'][0].update(op='LOAD', arg=0); self.reject(data, 'uninitialized')
    def test_invalid_constant(self):
        data = self.artifact(); data['functions']['bidaya']['code'][0]['arg'] = []; self.reject(data, 'constant')
    def test_invalid_call(self):
        data = self.artifact(); data['functions']['bidaya']['code'][0].update(op='CALL', arg=['missing', 0]); self.reject(data, 'call signature')
    def test_nonfinite_constant(self):
        data = self.artifact(); data['functions']['bidaya']['code'][0]['arg'] = float('inf'); self.reject(data, 'constant')

    def code_artifact(self, code, slots=0):
        data = self.artifact()
        data['functions']['bidaya']['slots'] = slots
        data['functions']['bidaya']['code'] = [
            {'op': op, 'arg': arg, 'span': {'line': 1, 'column': 1, 'length': 1}} for op, arg in code]
        return data

    def test_stack_height_join(self):
        data = self.code_artifact([('CONST', True), ('JZ', 4), ('CONST', 1), ('JMP', 5), ('JMP', 5), ('RET', None)])
        self.reject(data, 'Inconsistent stack height')

    def test_initialization_intersection(self):
        data = self.code_artifact([('CONST', True), ('JZ', 5), ('CONST', 1), ('STORE', 0),
                                   ('JMP', 6), ('JMP', 6), ('LOAD', 0), ('POP', None),
                                   ('CONST', None), ('RET', None)], slots=1)
        self.reject(data, 'uninitialized')

    def test_control_flow_falloff(self):
        self.reject(self.code_artifact([('CONST', 1)]), 'falls off')

    def test_extra_return_values(self):
        self.reject(self.code_artifact([('CONST', 1), ('CONST', 2), ('RET', None)]), 'exactly one')

    def test_invalid_runtime_operand_is_diagnostic(self):
        data = self.code_artifact([('CONST', 'string'), ('CONST', 1), ('BINARY', '-'), ('RET', None)])
        with self.assertRaisesRegex(ArabiziError, 'Invalid bytecode operand'):
            VM(loads(json.dumps(data))).run()

    def test_boolean_version_rejected(self):
        data = self.artifact(); data['version'] = True; self.reject(data, 'version')


class CLITests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'arabizi', *args], cwd=ROOT, capture_output=True, text=True)

    def test_run(self):
        result = self.cli('run', 'examples/factorial.az')
        self.assertEqual(result.returncode, 0); self.assertIn('3628800', result.stdout)
    def test_error_exit(self):
        result = self.cli('check', 'examples/type_error.az')
        self.assertEqual(result.returncode, 1); self.assertIn('Expected raqm, got nass', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
    def test_missing_file(self):
        result = self.cli('run', 'missing.az')
        self.assertEqual(result.returncode, 1); self.assertNotIn('Traceback', result.stderr)
    def test_trace(self):
        result = self.cli('run', 'examples/factorial.az', '--trace')
        self.assertEqual(result.returncode, 0); self.assertIn('CALL', result.stderr)
    def test_inspection_commands(self):
        for command in ('tokens', 'ast', 'ir', 'disasm', 'check'):
            result = self.cli(command, 'examples/riyadh.az')
            self.assertEqual(result.returncode, 0, result.stderr)
    def test_compile_reload(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp)/'example.azbc')
            result = self.cli('compile', 'examples/riyadh.az', '-o', path)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.cli('run', path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.endswith('41\n'))


if __name__ == '__main__': unittest.main()
