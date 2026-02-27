#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


# =====================
# LEXER
# =====================

KEYWORDS = {"let", "fn", "match", "with", "true", "false"}


@dataclass
class Token:
    kind: str
    value: str
    pos: int


class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.i = 0

    def peek(self) -> str:
        return self.src[self.i] if self.i < len(self.src) else "\0"

    def advance(self) -> str:
        ch = self.peek()
        self.i += 1
        return ch

    def skip_ws_and_comments(self) -> None:
        while True:
            while self.peek().isspace():
                self.advance()
            if self.peek() == "#":
                while self.peek() not in ("\n", "\0"):
                    self.advance()
            else:
                break

    def lex_number(self, start: int) -> Token:
        s = ""
        dot_count = 0
        while self.peek().isdigit() or self.peek() == ".":
            if self.peek() == ".":
                dot_count += 1
            s += self.advance()
        if dot_count > 1:
            raise SyntaxError(f"Invalid number '{s}' at {start}")
        return Token("NUMBER", s, start)

    def lex_ident(self, start: int) -> Token:
        s = ""
        while self.peek().isalnum() or self.peek() == "_":
            s += self.advance()
        if s in KEYWORDS:
            return Token("KW", s, start)
        return Token("IDENT", s, start)

    def lex_string(self, start: int) -> Token:
        self.advance()  # opening quote
        out = ""
        while self.peek() not in ('"', "\0"):
            ch = self.advance()
            if ch == "\\":
                nxt = self.advance()
                escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
                out += escapes.get(nxt, nxt)
            else:
                out += ch
        if self.peek() != '"':
            raise SyntaxError(f"Unterminated string at {start}")
        self.advance()
        return Token("STRING", out, start)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        two_char = {"=>", "==", "!=", "<=", ">=", "|>"}
        one_char = set("+-*/(){}[],:;=<>")

        while self.peek() != "\0":
            self.skip_ws_and_comments()
            start = self.i
            ch = self.peek()
            if ch == "\0":
                break
            if ch.isdigit():
                tokens.append(self.lex_number(start))
            elif ch.isalpha() or ch == "_":
                tokens.append(self.lex_ident(start))
            elif ch == '"':
                tokens.append(self.lex_string(start))
            else:
                pair = self.src[self.i:self.i + 2]
                if pair in two_char:
                    self.i += 2
                    tokens.append(Token("SYM", pair, start))
                elif ch in one_char:
                    self.advance()
                    tokens.append(Token("SYM", ch, start))
                else:
                    raise SyntaxError(f"Unexpected character '{ch}' at {start}")
        tokens.append(Token("EOF", "", self.i))
        return tokens


# =====================
# AST
# =====================


class Expr:
    pass


@dataclass
class Number(Expr):
    value: float


@dataclass
class String(Expr):
    value: str


@dataclass
class Bool(Expr):
    value: bool


@dataclass
class Identifier(Expr):
    name: str


@dataclass
class ListLit(Expr):
    items: List[Expr]


@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass
class Call(Expr):
    fn: Expr
    args: List[Expr]


@dataclass
class MatchCase:
    pattern: "Pattern"
    expr: Expr


@dataclass
class MatchExpr(Expr):
    target: Expr
    cases: List[MatchCase]


class Stmt:
    pass


@dataclass
class LetStmt(Stmt):
    name: str
    expr: Expr


@dataclass
class FnStmt(Stmt):
    name: str
    params: List[str]
    body: Expr


@dataclass
class ExprStmt(Stmt):
    expr: Expr


# Patterns
class Pattern:
    pass


@dataclass
class WildcardPat(Pattern):
    pass


@dataclass
class IdentPat(Pattern):
    name: str


@dataclass
class NumberPat(Pattern):
    value: float


@dataclass
class StringPat(Pattern):
    value: str


@dataclass
class BoolPat(Pattern):
    value: bool


@dataclass
class ListPat(Pattern):
    items: List[Pattern]


# =====================
# PARSER
# =====================


class Parser:
    PRECEDENCE = {
        "|>": 1,
        "==": 2,
        "!=": 2,
        "<": 3,
        "<=": 3,
        ">": 3,
        ">=": 3,
        "+": 4,
        "-": 4,
        "*": 5,
        "/": 5,
    }

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        t = self.peek()
        self.i += 1
        return t

    def expect(self, kind: str, value: Optional[str] = None) -> Token:
        t = self.peek()
        if t.kind != kind or (value is not None and t.value != value):
            raise SyntaxError(f"Expected {kind}:{value}, got {t.kind}:{t.value} at {t.pos}")
        return self.advance()

    def parse_program(self) -> List[Stmt]:
        out: List[Stmt] = []
        while self.peek().kind != "EOF":
            out.append(self.parse_stmt())
        return out

    def parse_stmt(self) -> Stmt:
        t = self.peek()
        if t.kind == "KW" and t.value == "let":
            self.advance()
            name = self.expect("IDENT").value
            self.expect("SYM", "=")
            expr = self.parse_expr()
            self.expect("SYM", ";")
            return LetStmt(name, expr)
        if t.kind == "KW" and t.value == "fn":
            self.advance()
            name = self.expect("IDENT").value
            self.expect("SYM", "(")
            params: List[str] = []
            if not (self.peek().kind == "SYM" and self.peek().value == ")"):
                while True:
                    params.append(self.expect("IDENT").value)
                    if self.peek().kind == "SYM" and self.peek().value == ",":
                        self.advance()
                        continue
                    break
            self.expect("SYM", ")")
            self.expect("SYM", "=>")
            body = self.parse_expr()
            self.expect("SYM", ";")
            return FnStmt(name, params, body)

        expr = self.parse_expr()
        self.expect("SYM", ";")
        return ExprStmt(expr)

    def parse_expr(self, min_prec: int = 0) -> Expr:
        left = self.parse_primary()
        while True:
            t = self.peek()
            if t.kind == "SYM" and t.value == "(":
                left = self.parse_call(left)
                continue
            if t.kind != "SYM" or t.value not in self.PRECEDENCE:
                break
            prec = self.PRECEDENCE[t.value]
            if prec < min_prec:
                break
            op = self.advance().value
            right = self.parse_expr(prec + 1)
            left = Binary(op, left, right)
        return left

    def parse_call(self, fn_expr: Expr) -> Expr:
        self.expect("SYM", "(")
        args: List[Expr] = []
        if not (self.peek().kind == "SYM" and self.peek().value == ")"):
            while True:
                args.append(self.parse_expr())
                if self.peek().kind == "SYM" and self.peek().value == ",":
                    self.advance()
                    continue
                break
        self.expect("SYM", ")")
        return Call(fn_expr, args)

    def parse_primary(self) -> Expr:
        t = self.peek()
        if t.kind == "NUMBER":
            self.advance()
            return Number(float(t.value))
        if t.kind == "STRING":
            self.advance()
            return String(t.value)
        if t.kind == "IDENT":
            self.advance()
            return Identifier(t.value)
        if t.kind == "KW" and t.value in ("true", "false"):
            self.advance()
            return Bool(t.value == "true")
        if t.kind == "SYM" and t.value == "(":
            self.advance()
            expr = self.parse_expr()
            self.expect("SYM", ")")
            return expr
        if t.kind == "SYM" and t.value == "[":
            self.advance()
            items: List[Expr] = []
            if not (self.peek().kind == "SYM" and self.peek().value == "]"):
                while True:
                    items.append(self.parse_expr())
                    if self.peek().kind == "SYM" and self.peek().value == ",":
                        self.advance()
                        continue
                    break
            self.expect("SYM", "]")
            return ListLit(items)
        if t.kind == "KW" and t.value == "match":
            return self.parse_match_expr()
        raise SyntaxError(f"Unexpected token {t.kind}:{t.value} at {t.pos}")

    def parse_match_expr(self) -> Expr:
        self.expect("KW", "match")
        target = self.parse_expr()
        self.expect("KW", "with")
        cases: List[MatchCase] = []
        while True:
            pat = self.parse_pattern()
            self.expect("SYM", "=>")
            body = self.parse_expr()
            cases.append(MatchCase(pat, body))
            if self.peek().kind == "SYM" and self.peek().value == ";":
                break
        return MatchExpr(target, cases)

    def parse_pattern(self) -> Pattern:
        t = self.peek()
        if t.kind == "IDENT" and t.value == "_":
            self.advance()
            return WildcardPat()
        if t.kind == "IDENT":
            self.advance()
            return IdentPat(t.value)
        if t.kind == "NUMBER":
            self.advance()
            return NumberPat(float(t.value))
        if t.kind == "STRING":
            self.advance()
            return StringPat(t.value)
        if t.kind == "KW" and t.value in ("true", "false"):
            self.advance()
            return BoolPat(t.value == "true")
        if t.kind == "SYM" and t.value == "[":
            self.advance()
            pats: List[Pattern] = []
            if not (self.peek().kind == "SYM" and self.peek().value == "]"):
                while True:
                    pats.append(self.parse_pattern())
                    if self.peek().kind == "SYM" and self.peek().value == ",":
                        self.advance()
                        continue
                    break
            self.expect("SYM", "]")
            return ListPat(pats)
        raise SyntaxError(f"Invalid pattern {t.kind}:{t.value} at {t.pos}")


# =====================
# TYPE INFERENCE
# =====================


class Type:
    name: str

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


INT = Type("Int")
FLOAT = Type("Float")
BOOL_T = Type("Bool")
STRING_T = Type("String")
UNKNOWN = Type("Unknown")


@dataclass
class ListType(Type):
    inner: Type

    def __init__(self, inner: Type):
        super().__init__(f"List[{inner}]")
        self.inner = inner


@dataclass
class FunctionType(Type):
    params: List[Type]
    ret: Type

    def __init__(self, params: List[Type], ret: Type):
        super().__init__("Function")
        self.params = params
        self.ret = ret


class TypeInferencer:
    def __init__(self):
        self.env: Dict[str, Type] = {}

    def infer_program(self, stmts: List[Stmt]) -> Dict[str, Type]:
        for stmt in stmts:
            if isinstance(stmt, LetStmt):
                self.env[stmt.name] = self.infer_expr(stmt.expr)
            elif isinstance(stmt, FnStmt):
                params = [UNKNOWN for _ in stmt.params]
                local = dict(self.env)
                for p in stmt.params:
                    local[p] = UNKNOWN
                old = self.env
                self.env = local
                ret = self.infer_expr(stmt.body)
                self.env = old
                self.env[stmt.name] = FunctionType(params, ret)
            elif isinstance(stmt, ExprStmt):
                self.infer_expr(stmt.expr)
        return self.env

    def infer_expr(self, expr: Expr) -> Type:
        if isinstance(expr, Number):
            return INT if expr.value.is_integer() else FLOAT
        if isinstance(expr, String):
            return STRING_T
        if isinstance(expr, Bool):
            return BOOL_T
        if isinstance(expr, Identifier):
            return self.env.get(expr.name, UNKNOWN)
        if isinstance(expr, ListLit):
            if not expr.items:
                return ListType(UNKNOWN)
            inner = self.infer_expr(expr.items[0])
            return ListType(inner)
        if isinstance(expr, Binary):
            lt = self.infer_expr(expr.left)
            rt = self.infer_expr(expr.right)
            if expr.op in {"+", "-", "*", "/"}:
                if STRING_T in (lt, rt) and expr.op == "+":
                    return STRING_T
                if FLOAT in (lt, rt):
                    return FLOAT
                if lt == INT and rt == INT:
                    return INT
                return UNKNOWN
            if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
                return BOOL_T
            if expr.op == "|>":
                if isinstance(expr.right, Identifier):
                    fn_t = self.env.get(expr.right.name, UNKNOWN)
                    if isinstance(fn_t, FunctionType):
                        return fn_t.ret
                return UNKNOWN
            return UNKNOWN
        if isinstance(expr, Call):
            fn_t = self.infer_expr(expr.fn)
            if isinstance(fn_t, FunctionType):
                return fn_t.ret
            return UNKNOWN
        if isinstance(expr, MatchExpr):
            if not expr.cases:
                return UNKNOWN
            return self.infer_expr(expr.cases[0].expr)
        return UNKNOWN


# =====================
# OPTIMIZER
# =====================


def constant_fold(expr: Expr) -> Expr:
    if isinstance(expr, Binary):
        left = constant_fold(expr.left)
        right = constant_fold(expr.right)
        if isinstance(left, Number) and isinstance(right, Number):
            if expr.op == "+":
                return Number(left.value + right.value)
            if expr.op == "-":
                return Number(left.value - right.value)
            if expr.op == "*":
                return Number(left.value * right.value)
            if expr.op == "/":
                return Number(left.value / right.value)
            if expr.op == "==":
                return Bool(left.value == right.value)
        return Binary(expr.op, left, right)
    if isinstance(expr, Call):
        return Call(constant_fold(expr.fn), [constant_fold(a) for a in expr.args])
    if isinstance(expr, MatchExpr):
        return MatchExpr(constant_fold(expr.target), [MatchCase(c.pattern, constant_fold(c.expr)) for c in expr.cases])
    if isinstance(expr, ListLit):
        return ListLit([constant_fold(i) for i in expr.items])
    return expr


def optimize(stmts: List[Stmt]) -> List[Stmt]:
    out: List[Stmt] = []
    for s in stmts:
        if isinstance(s, LetStmt):
            out.append(LetStmt(s.name, constant_fold(s.expr)))
        elif isinstance(s, FnStmt):
            out.append(FnStmt(s.name, s.params, constant_fold(s.body)))
        else:
            out.append(ExprStmt(constant_fold(s.expr)))
    return out


# =====================
# EVALUATOR
# =====================


@dataclass
class UserFunction:
    params: List[str]
    body: Expr
    closure: Dict[str, Any]


class Evaluator:
    def __init__(self):
        self.env: Dict[str, Any] = {}
        self.env.update({
            "print": lambda x: print(self.pretty(x)) or x,
            "len": lambda x: len(x),
            "head": lambda x: x[0],
            "tail": lambda x: x[1:],
        })

    @staticmethod
    def pretty(v: Any) -> str:
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)

    def run(self, stmts: List[Stmt]) -> Any:
        last = None
        for s in stmts:
            if isinstance(s, LetStmt):
                self.env[s.name] = self.eval_expr(s.expr)
            elif isinstance(s, FnStmt):
                fn = UserFunction(s.params, s.body, dict(self.env))
                fn.closure[s.name] = fn
                self.env[s.name] = fn
            elif isinstance(s, ExprStmt):
                last = self.eval_expr(s.expr)
        return last

    def eval_expr(self, expr: Expr) -> Any:
        if isinstance(expr, Number):
            return expr.value
        if isinstance(expr, String):
            return expr.value
        if isinstance(expr, Bool):
            return expr.value
        if isinstance(expr, Identifier):
            if expr.name not in self.env:
                raise NameError(f"Undefined variable '{expr.name}'")
            return self.env[expr.name]
        if isinstance(expr, ListLit):
            return [self.eval_expr(x) for x in expr.items]
        if isinstance(expr, Binary):
            if expr.op == "|>":
                val = self.eval_expr(expr.left)
                fn = self.eval_expr(expr.right)
                return self.apply(fn, [val])
            l = self.eval_expr(expr.left)
            r = self.eval_expr(expr.right)
            if expr.op == "+":
                return l + r
            if expr.op == "-":
                return l - r
            if expr.op == "*":
                return l * r
            if expr.op == "/":
                return l / r
            if expr.op == "==":
                return l == r
            if expr.op == "!=":
                return l != r
            if expr.op == "<":
                return l < r
            if expr.op == "<=":
                return l <= r
            if expr.op == ">":
                return l > r
            if expr.op == ">=":
                return l >= r
            raise RuntimeError(f"Unknown operator {expr.op}")
        if isinstance(expr, Call):
            fn = self.eval_expr(expr.fn)
            args = [self.eval_expr(a) for a in expr.args]
            return self.apply(fn, args)
        if isinstance(expr, MatchExpr):
            target = self.eval_expr(expr.target)
            for case in expr.cases:
                binds: Dict[str, Any] = {}
                if self.match_pattern(case.pattern, target, binds):
                    old = dict(self.env)
                    self.env.update(binds)
                    result = self.eval_expr(case.expr)
                    self.env = old
                    return result
            raise RuntimeError("Non-exhaustive match")
        raise RuntimeError(f"Unknown expr: {expr}")

    def apply(self, fn: Any, args: List[Any]) -> Any:
        if callable(fn):
            return fn(*args)
        if isinstance(fn, UserFunction):
            if len(args) != len(fn.params):
                raise TypeError("arity mismatch")
            old = self.env
            self.env = dict(fn.closure)
            self.env.update({p: a for p, a in zip(fn.params, args)})
            result = self.eval_expr(fn.body)
            self.env = old
            return result
        raise TypeError("Not callable")

    def match_pattern(self, pat: Pattern, value: Any, out: Dict[str, Any]) -> bool:
        if isinstance(pat, WildcardPat):
            return True
        if isinstance(pat, IdentPat):
            out[pat.name] = value
            return True
        if isinstance(pat, NumberPat):
            return value == pat.value
        if isinstance(pat, StringPat):
            return value == pat.value
        if isinstance(pat, BoolPat):
            return value == pat.value
        if isinstance(pat, ListPat):
            if not isinstance(value, list) or len(value) != len(pat.items):
                return False
            for p, v in zip(pat.items, value):
                if not self.match_pattern(p, v, out):
                    return False
            return True
        return False


def run_source(src: str, infer_only: bool = False) -> Tuple[Any, Dict[str, Type]]:
    tokens = Lexer(src).tokenize()
    stmts = Parser(tokens).parse_program()
    types = TypeInferencer().infer_program(stmts)
    if infer_only:
        return None, types
    optimized = optimize(stmts)
    result = Evaluator().run(optimized)
    return result, types


def main() -> None:
    ap = argparse.ArgumentParser(description="Nebula language runtime")
    ap.add_argument("file", help="Nebula source file")
    ap.add_argument("--types", action="store_true", help="Only print inferred top-level types")
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        src = f.read()

    result, types = run_source(src, infer_only=args.types)
    if args.types:
        for k, v in types.items():
            print(f"{k}: {v}")
    elif result is not None:
        print(Evaluator.pretty(result))


if __name__ == "__main__":
    main()
