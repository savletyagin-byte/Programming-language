import unittest

from nebula import Lexer, Parser, optimize, LetStmt, Number, Bool, run_source


class NebulaTests(unittest.TestCase):
    def test_pipeline_with_placeholder(self):
        src = """
let xs = [1, 2, 3, 4];
xs |> reduce(_, 0, fun(acc, x) => acc + x);
"""
        result, _ = run_source(src)
        self.assertEqual(result, 10)

    def test_if_expression_and_recursion(self):
        src = """
fn fact(n) => if n <= 1 then 1 else n * fact(n - 1);
fact(6);
"""
        result, _ = run_source(src)
        self.assertEqual(result, 720)

    def test_dict_member_and_index(self):
        src = """
let cfg = {name: "nebula", weights: [2, 3, 5]};
cfg.weights[1];
"""
        result, _ = run_source(src)
        self.assertEqual(result, 3)

    def test_type_inference_reports_function_shape(self):
        src = """
fn add(a, b) => a + b;
let cfg = {timeout: 30, label: "prod"};
"""
        _, types = run_source(src, infer_only=True)
        self.assertIn("add", types)
        self.assertIn("cfg", types)
        self.assertIn("Function", str(types["add"]))
        self.assertIn("Dict", str(types["cfg"]))

    def test_option_adt_pattern_matching(self):
        src = """
let x = Some(41);
match x with
  Some(v) => v + 1
  None() => 0;
"""
        result, _ = run_source(src)
        self.assertEqual(result, 42)

    def test_move_checker_use_after_move(self):
        src = """
let x = [1,2,3];
move(x);
x;
"""
        with self.assertRaises(SyntaxError):
            run_source(src)

    def test_macro_expansion(self):
        src = """
macro_inc(5);
"""
        result, _ = run_source(src)
        self.assertEqual(result, 6)

    def test_concurrency_spawn_join_and_channels(self):
        src = """
fn sq(n) => n * n;
let task = spawn(sq, 12);
let ch = channel();
send(ch, join(task));
recv(ch);
"""
        result, _ = run_source(src)
        self.assertEqual(result, 144)

    def test_result_adt_pattern_matching(self):
        src = """
let r = Ok(9);
match r with
  Ok(v) => v + 1
  Err(e) => 0;
"""
        result, _ = run_source(src)
        self.assertEqual(result, 10)

    def test_result_exhaustiveness_check(self):
        src = """
let r = Ok(1);
match r with
  Ok(v) => v;
"""
        with self.assertRaises(SyntaxError):
            run_source(src)

    def test_parallel_map_and_json(self):
        src = """
fn sq(x) => x * x;
let out = par_map([1,2,3], sq);
let packed = json_encode({vals: out});
json_decode(packed).vals[2];
"""
        result, _ = run_source(src)
        self.assertEqual(result, 9)

    def test_try_recv_default(self):
        src = """
let ch = channel();
try_recv(ch, 123);
"""
        result, _ = run_source(src)
        self.assertEqual(result, 123)

    def test_macro_assert(self):
        src = """
macro_assert(2 < 3, 99);
"""
        result, _ = run_source(src)
        self.assertEqual(result, 99)

    def test_neural_network_xor_training(self):
        src = """
let model = nn_train_xor(3500, 0.5, 7);
let p00 = nn_predict(model, [0, 0])[0];
let p01 = nn_predict(model, [0, 1])[0];
let p10 = nn_predict(model, [1, 0])[0];
let p11 = nn_predict(model, [1, 1])[0];
[p00 < 0.2, p01 > 0.8, p10 > 0.8, p11 < 0.2];
"""
        result, _ = run_source(src)
        self.assertEqual(result, [True, True, True, True])

    def test_constant_fold_arithmetic_and_boolean(self):
        tokens = Lexer("let x = if true then 2 + 3 else 0;".strip()).tokenize()
        stmts = Parser(tokens).parse_program()
        opt = optimize(stmts)
        self.assertIsInstance(opt[0], LetStmt)
        self.assertIsInstance(opt[0].expr, Number)
        self.assertEqual(opt[0].expr.value, 5)

        tokens2 = Lexer("let y = not false;".strip()).tokenize()
        stmts2 = Parser(tokens2).parse_program()
        opt2 = optimize(stmts2)
        self.assertIsInstance(opt2[0].expr, Bool)
        self.assertEqual(opt2[0].expr.value, True)


if __name__ == "__main__":
    unittest.main()
