import unittest

from nebula import run_source, Lexer, Parser, optimize, LetStmt, Number


class NebulaTests(unittest.TestCase):
    def test_pipeline(self):
        src = """
fn inc(n) => n + 1;
fn dbl(n) => n * 2;
5 |> inc |> dbl;
"""
        result, _ = run_source(src)
        self.assertEqual(result, 12)

    def test_pattern_match(self):
        src = """
let x = [10, 20];
match x with
  [a, b] => a + b
  _ => 0;
"""
        result, _ = run_source(src)
        self.assertEqual(result, 30)

    def test_type_inference(self):
        src = """
fn add(a, b) => a + b;
let x = 4;
"""
        _, types = run_source(src, infer_only=True)
        self.assertIn("add", types)
        self.assertIn("x", types)
        self.assertEqual(str(types["x"]), "Int")

    def test_constant_fold(self):
        tokens = Lexer("let x = 2 + 3;".strip()).tokenize()
        stmts = Parser(tokens).parse_program()
        opt = optimize(stmts)
        self.assertIsInstance(opt[0], LetStmt)
        self.assertIsInstance(opt[0].expr, Number)
        self.assertEqual(opt[0].expr.value, 5)


if __name__ == "__main__":
    unittest.main()
