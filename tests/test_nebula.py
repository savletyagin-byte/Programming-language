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
