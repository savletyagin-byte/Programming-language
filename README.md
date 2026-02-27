# Nebula: Hyper-Advanced Experimental Programming Language

Nebula is a compact but feature-dense language runtime with a full pipeline:

1. Lexing
2. Pratt parsing
3. Static type inference
4. AST optimization (constant folding)
5. Evaluation with closures

## Advanced feature set

- First-class functions + lexical closures + recursion
- Anonymous functions (`fun(...) => ...`)
- Functional pipelines (`|>`) with placeholder injection (`_`)
- Pattern matching with destructuring
- Expression-based control flow (`if ... then ... else ...`)
- List + dictionary literals
- Member access (`config.timeout`) and indexing (`arr[0]`, `dict["k"]`)
- Partial application/currying for user-defined functions
- Higher-order built-ins (`map`, `filter`, `reduce`, `range`, etc.)
- Built-in neural network primitives (`nn_create`, `nn_predict`, `nn_train_xor`)
- Memory safety analysis via ownership-style move checks (`move(x)` + compile-time use-after-move errors)
- Null safety with Option ADT (`Some(v)` / `None()`)
- ADT-style constructor pattern matching with exhaustiveness checks for Option
- Concurrency primitives (`spawn`, `join`, `channel`, `send`, `recv`)
- Compile-time metaprogramming macros (`macro_inc`, `macro_when`)

## Quick start

```bash
python3 nebula.py examples/extreme.neb
python3 nebula.py --types examples/extreme.neb
python3 nebula.py examples/neural.neb
```

## Syntax highlights

```nebula
fn fact(n) => if n <= 1 then 1 else n * fact(n - 1);
let data = {title: "Nebula", version: 2};
let nums = range(6) |> map(fun(x) => x * x);
nums |> filter(fun(x) => x > 10) |> reduce(0, fun(acc, x) => acc + x) |> print;
```

## Neural networks

Nebula includes built-ins for simple feed-forward neural networks with backprop training:

```nebula
let model = nn_train_xor(3500, 0.5, 7);
let out = nn_predict(model, [0, 1])[0];
out |> print;
```

## Advanced safety & type-oriented model

- **Immutability by default**: `let` bindings are immutable; no reassignment exists.
- **Memory safety without GC pauses**: a compile-time move checker rejects use-after-move and double-move patterns.
- **Strong static typing with inference**: top-level values and functions are inferred (including Option and function shapes).
- **Null safety**: model absence with `None()` and presence with `Some(value)`; use pattern matching or `unwrap_or`.

```nebula
let maybe = Some(10);
match maybe with
  Some(v) => v + 1
  None() => 0;
```

## Concurrency

```nebula
fn work(x) => x * x;
let t = spawn(work, 9);
let ch = channel();
send(ch, join(t));
recv(ch) |> print;
```

## Macros (compile-time AST rewrites)

```nebula
macro_inc(41) |> print;
macro_when(true, 10, 0) |> print;
```
