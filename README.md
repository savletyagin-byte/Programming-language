# Nebula: An Advanced Experimental Programming Language

Nebula is a **high-level, expression-first programming language** implemented in Python in this repository. It is designed to feel modern and powerful while still being small enough to inspect end-to-end.

## What makes Nebula "advanced"

Nebula includes several advanced language ideas in one coherent runtime:

- **First-class functions and lexical closures**
- **Immutable-style expression evaluation** with explicit `let` bindings
- **Pattern matching** with destructuring (`[head, tail]`) and wildcard (`_`)
- **Pipeline operator (`|>`)** for readable dataflow composition
- **User functions + recursion**
- **Static type inference pass** (Int, Float, Bool, String, List, Function, Unknown)
- **Constant-fold optimization pass** before execution
- **Tree-walk runtime with built-ins**

Even as an experimental implementation, Nebula has a full compile pipeline:

1. Lexing
2. Parsing (Pratt parser)
3. Static type inference
4. Optimization
5. Evaluation

## Quick start

```bash
python3 nebula.py examples/fib.neb
```

Run tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Language tour

### Let bindings and functions

```nebula
let x = 40;
let y = 2;
fn add(a, b) => a + b;
print(add(x, y));
```

### Pattern matching

```nebula
let pair = [10, 20];
match pair with
  [a, b] => a + b
  _ => 0;
```

### Pipeline style

```nebula
fn inc(n) => n + 1;
fn double(n) => n * 2;

5 |> inc |> double |> print;
```

## Files

- `nebula.py` — complete implementation (lexer, parser, inference, optimizer, evaluator, CLI)
- `examples/fib.neb` — recursive function + pipeline demo
- `examples/match.neb` — pattern matching demo
- `tests/test_nebula.py` — parser/runtime/type-inference/optimization tests

## Notes

This project is intentionally self-contained and dependency-free (Python standard library only).
