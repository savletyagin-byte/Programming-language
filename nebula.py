#!/usr/bin/env python3
from __future__ import annotations

import argparse
import functools
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# =====================
# LEXER
# =====================

KEYWORDS = {
    "let",
    "fn",
    "fun",
    "match",
    "with",
    "if",
    "then",
    "else",
    "true",
    "false",
    "not",
}


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
        self.advance()
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
        two_char = {"=>", "==", "!=", "<=", ">=", "|>", "&&", "||"}
        one_char = set("+-*/(){}[],:;=<>.")

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
class DictLit(Expr):
    items: List[Tuple[str, Expr]]


@dataclass
class Unary(Expr):
    op: str
    expr: Expr


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
class IndexExpr(Expr):
    target: Expr
    index: Expr


@dataclass
class MemberExpr(Expr):
    target: Expr
    name: str


@dataclass
class FunctionExpr(Expr):
    params: List[str]
    body: Expr


@dataclass
class IfExpr(Expr):
    cond: Expr
    then_expr: Expr
    else_expr: Expr


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
        "||": 1,
        "&&": 2,
        "|>": 3,
        "==": 4,
        "!=": 4,
        "<": 5,
        "<=": 5,
        ">": 5,
        ">=": 5,
        "+": 6,
        "-": 6,
        "*": 7,
        "/": 7,
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
            params = self.parse_params()
            self.expect("SYM", "=>")
            body = self.parse_expr()
            self.expect("SYM", ";")
            return FnStmt(name, params, body)
        expr = self.parse_expr()
        self.expect("SYM", ";")
        return ExprStmt(expr)

    def parse_params(self) -> List[str]:
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
        return params

    def parse_expr(self, min_prec: int = 0) -> Expr:
        left = self.parse_prefix()
        while True:
            t = self.peek()
            if t.kind == "SYM" and t.value in ("(", "[", "."):
                left = self.parse_postfix(left)
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

    def parse_postfix(self, left: Expr) -> Expr:
        t = self.peek()
        if t.kind == "SYM" and t.value == "(":
            self.advance()
            args: List[Expr] = []
            if not (self.peek().kind == "SYM" and self.peek().value == ")"):
                while True:
                    args.append(self.parse_expr())
                    if self.peek().kind == "SYM" and self.peek().value == ",":
                        self.advance()
                        continue
                    break
            self.expect("SYM", ")")
            return Call(left, args)
        if t.kind == "SYM" and t.value == "[":
            self.advance()
            index = self.parse_expr()
            self.expect("SYM", "]")
            return IndexExpr(left, index)
        if t.kind == "SYM" and t.value == ".":
            self.advance()
            name = self.expect("IDENT").value
            return MemberExpr(left, name)
        raise SyntaxError("invalid postfix")

    def parse_prefix(self) -> Expr:
        t = self.peek()
        if t.kind == "SYM" and t.value == "-":
            self.advance()
            return Unary("-", self.parse_expr(8))
        if t.kind == "KW" and t.value == "not":
            self.advance()
            return Unary("not", self.parse_expr(8))
        return self.parse_primary()

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
        if t.kind == "SYM" and t.value == "{":
            return self.parse_dict_literal()
        if t.kind == "KW" and t.value == "if":
            return self.parse_if_expr()
        if t.kind == "KW" and t.value == "fun":
            self.advance()
            params = self.parse_params()
            self.expect("SYM", "=>")
            return FunctionExpr(params, self.parse_expr())
        if t.kind == "KW" and t.value == "match":
            return self.parse_match_expr()
        raise SyntaxError(f"Unexpected token {t.kind}:{t.value} at {t.pos}")

    def parse_if_expr(self) -> Expr:
        self.expect("KW", "if")
        cond = self.parse_expr()
        self.expect("KW", "then")
        then_expr = self.parse_expr()
        self.expect("KW", "else")
        else_expr = self.parse_expr()
        return IfExpr(cond, then_expr, else_expr)

    def parse_dict_literal(self) -> Expr:
        self.expect("SYM", "{")
        items: List[Tuple[str, Expr]] = []
        if not (self.peek().kind == "SYM" and self.peek().value == "}"):
            while True:
                key_tok = self.peek()
                if key_tok.kind == "STRING":
                    key = self.advance().value
                elif key_tok.kind == "IDENT":
                    key = self.advance().value
                else:
                    raise SyntaxError("Dict keys must be identifiers or strings")
                self.expect("SYM", ":")
                value = self.parse_expr()
                items.append((key, value))
                if self.peek().kind == "SYM" and self.peek().value == ",":
                    self.advance()
                    continue
                break
        self.expect("SYM", "}")
        return DictLit(items)

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
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


INT = Type("Int")
FLOAT = Type("Float")
BOOL_T = Type("Bool")
STRING_T = Type("String")
UNKNOWN = Type("Unknown")


class ListType(Type):
    def __init__(self, inner: Type):
        super().__init__(f"List[{inner}]")
        self.inner = inner


class DictType(Type):
    def __init__(self, keys: Dict[str, Type]):
        super().__init__("Dict")
        self.keys = keys

    def __repr__(self) -> str:
        if not self.keys:
            return "Dict{}"
        body = ", ".join(f"{k}: {v}" for k, v in sorted(self.keys.items()))
        return f"Dict{{{body}}}"


class FunctionType(Type):
    def __init__(self, params: List[Type], ret: Type):
        super().__init__("Function")
        self.params = params
        self.ret = ret

    def __repr__(self) -> str:
        return f"Function({', '.join(map(str, self.params))}) -> {self.ret}"


def type_join(a: Type, b: Type) -> Type:
    if a == b:
        return a
    if a == UNKNOWN:
        return b
    if b == UNKNOWN:
        return a
    if (a, b) in {(INT, FLOAT), (FLOAT, INT)}:
        return FLOAT
    return UNKNOWN


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
                fn_type = FunctionType(params, UNKNOWN)
                local[stmt.name] = fn_type
                old = self.env
                self.env = local
                fn_type.ret = self.infer_expr(stmt.body)
                self.env = old
                self.env[stmt.name] = fn_type
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
            for item in expr.items[1:]:
                inner = type_join(inner, self.infer_expr(item))
            return ListType(inner)
        if isinstance(expr, DictLit):
            return DictType({k: self.infer_expr(v) for k, v in expr.items})
        if isinstance(expr, Unary):
            if expr.op == "not":
                return BOOL_T
            return self.infer_expr(expr.expr)
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
            if expr.op in {"==", "!=", "<", "<=", ">", ">=", "&&", "||"}:
                return BOOL_T
            if expr.op == "|>":
                if isinstance(expr.right, Identifier):
                    fn_t = self.env.get(expr.right.name, UNKNOWN)
                    if isinstance(fn_t, FunctionType):
                        return fn_t.ret
                if isinstance(expr.right, Call):
                    callee_t = self.infer_expr(expr.right.fn)
                    if isinstance(callee_t, FunctionType):
                        return callee_t.ret
                return UNKNOWN
            return UNKNOWN
        if isinstance(expr, Call):
            fn_t = self.infer_expr(expr.fn)
            if isinstance(fn_t, FunctionType):
                return fn_t.ret
            return UNKNOWN
        if isinstance(expr, IndexExpr):
            tt = self.infer_expr(expr.target)
            if isinstance(tt, ListType):
                return tt.inner
            if isinstance(tt, DictType) and isinstance(expr.index, String):
                return tt.keys.get(expr.index.value, UNKNOWN)
            return UNKNOWN
        if isinstance(expr, MemberExpr):
            tt = self.infer_expr(expr.target)
            if isinstance(tt, DictType):
                return tt.keys.get(expr.name, UNKNOWN)
            return UNKNOWN
        if isinstance(expr, FunctionExpr):
            old = self.env
            local = dict(self.env)
            for p in expr.params:
                local[p] = UNKNOWN
            self.env = local
            ret = self.infer_expr(expr.body)
            self.env = old
            return FunctionType([UNKNOWN for _ in expr.params], ret)
        if isinstance(expr, IfExpr):
            return type_join(self.infer_expr(expr.then_expr), self.infer_expr(expr.else_expr))
        if isinstance(expr, MatchExpr):
            if not expr.cases:
                return UNKNOWN
            t = self.infer_expr(expr.cases[0].expr)
            for c in expr.cases[1:]:
                t = type_join(t, self.infer_expr(c.expr))
            return t
        return UNKNOWN


# =====================
# OPTIMIZER
# =====================


def constant_fold(expr: Expr) -> Expr:
    if isinstance(expr, Unary):
        inner = constant_fold(expr.expr)
        if isinstance(inner, Number) and expr.op == "-":
            return Number(-inner.value)
        if isinstance(inner, Bool) and expr.op == "not":
            return Bool(not inner.value)
        return Unary(expr.op, inner)
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
            if expr.op == "!=":
                return Bool(left.value != right.value)
            if expr.op == "<":
                return Bool(left.value < right.value)
            if expr.op == "<=":
                return Bool(left.value <= right.value)
            if expr.op == ">":
                return Bool(left.value > right.value)
            if expr.op == ">=":
                return Bool(left.value >= right.value)
        if isinstance(left, Bool) and isinstance(right, Bool):
            if expr.op == "&&":
                return Bool(left.value and right.value)
            if expr.op == "||":
                return Bool(left.value or right.value)
        return Binary(expr.op, left, right)
    if isinstance(expr, IfExpr):
        cond = constant_fold(expr.cond)
        then_expr = constant_fold(expr.then_expr)
        else_expr = constant_fold(expr.else_expr)
        if isinstance(cond, Bool):
            return then_expr if cond.value else else_expr
        return IfExpr(cond, then_expr, else_expr)
    if isinstance(expr, Call):
        return Call(constant_fold(expr.fn), [constant_fold(a) for a in expr.args])
    if isinstance(expr, IndexExpr):
        return IndexExpr(constant_fold(expr.target), constant_fold(expr.index))
    if isinstance(expr, MemberExpr):
        return MemberExpr(constant_fold(expr.target), expr.name)
    if isinstance(expr, FunctionExpr):
        return FunctionExpr(expr.params, constant_fold(expr.body))
    if isinstance(expr, MatchExpr):
        return MatchExpr(constant_fold(expr.target), [MatchCase(c.pattern, constant_fold(c.expr)) for c in expr.cases])
    if isinstance(expr, ListLit):
        return ListLit([constant_fold(i) for i in expr.items])
    if isinstance(expr, DictLit):
        return DictLit([(k, constant_fold(v)) for k, v in expr.items])
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
            "range": lambda n: list(range(int(n))),
            "map": lambda xs, fn: [self.apply(fn, [x]) for x in xs],
            "filter": lambda xs, fn: [x for x in xs if self.apply(fn, [x])],
            "reduce": lambda xs, init, fn: functools.reduce(lambda a, b: self.apply(fn, [a, b]), xs, init),
            "sort": lambda xs: sorted(xs),
            "keys": lambda d: list(d.keys()),
            "values": lambda d: list(d.values()),
            "type": lambda x: type(x).__name__,
            "assert": lambda cond, msg: cond if cond else (_raise(RuntimeError(str(msg)))),
            "nn_create": lambda inp, hid, out, seed=42: nn_create(int(inp), int(hid), int(out), int(seed)),
            "nn_predict": lambda model, features: nn_predict(model, features),
            "nn_train_xor": lambda epochs=3000, lr=0.5, seed=42: nn_train_xor(int(epochs), float(lr), int(seed)),
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
        if isinstance(expr, DictLit):
            return {k: self.eval_expr(v) for k, v in expr.items}
        if isinstance(expr, Unary):
            v = self.eval_expr(expr.expr)
            if expr.op == "-":
                return -v
            if expr.op == "not":
                return not v
            raise RuntimeError(f"Unknown unary operator {expr.op}")
        if isinstance(expr, Binary):
            if expr.op == "|>":
                return self.eval_pipeline(expr.left, expr.right)
            if expr.op == "&&":
                return bool(self.eval_expr(expr.left)) and bool(self.eval_expr(expr.right))
            if expr.op == "||":
                return bool(self.eval_expr(expr.left)) or bool(self.eval_expr(expr.right))
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
        if isinstance(expr, IndexExpr):
            target = self.eval_expr(expr.target)
            idx = self.eval_expr(expr.index)
            return target[int(idx)] if isinstance(target, list) else target[idx]
        if isinstance(expr, MemberExpr):
            target = self.eval_expr(expr.target)
            if isinstance(target, dict):
                if expr.name not in target:
                    raise KeyError(f"Missing key '{expr.name}'")
                return target[expr.name]
            raise TypeError("member access only works on dict values")
        if isinstance(expr, FunctionExpr):
            return UserFunction(expr.params, expr.body, dict(self.env))
        if isinstance(expr, IfExpr):
            return self.eval_expr(expr.then_expr if self.eval_expr(expr.cond) else expr.else_expr)
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

    def eval_pipeline(self, left: Expr, right: Expr) -> Any:
        value = self.eval_expr(left)
        if isinstance(right, Identifier):
            return self.apply(self.eval_expr(right), [value])
        if isinstance(right, Call):
            fn = self.eval_expr(right.fn)
            args: List[Any] = []
            used_placeholder = False
            for a in right.args:
                if isinstance(a, Identifier) and a.name == "_":
                    args.append(value)
                    used_placeholder = True
                else:
                    args.append(self.eval_expr(a))
            if not used_placeholder:
                args = [value] + args
            return self.apply(fn, args)
        return self.apply(self.eval_expr(right), [value])

    def apply(self, fn: Any, args: List[Any]) -> Any:
        if callable(fn):
            return fn(*args)
        if isinstance(fn, UserFunction):
            if len(args) < len(fn.params):
                bound = dict(fn.closure)
                for p, a in zip(fn.params, args):
                    bound[p] = a
                return UserFunction(fn.params[len(args):], fn.body, bound)
            if len(args) > len(fn.params):
                first = self.apply(fn, args[: len(fn.params)])
                return self.apply(first, args[len(fn.params):])
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




def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _dsigmoid(y: float) -> float:
    return y * (1.0 - y)


def nn_create(input_size: int, hidden_size: int, output_size: int, seed: int = 42) -> Dict[str, Any]:
    rng = random.Random(seed)
    w1 = [[rng.uniform(-1.0, 1.0) for _ in range(hidden_size)] for _ in range(input_size)]
    b1 = [0.0 for _ in range(hidden_size)]
    w2 = [[rng.uniform(-1.0, 1.0) for _ in range(output_size)] for _ in range(hidden_size)]
    b2 = [0.0 for _ in range(output_size)]
    return {
        "input": input_size,
        "hidden": hidden_size,
        "output": output_size,
        "w1": w1,
        "b1": b1,
        "w2": w2,
        "b2": b2,
    }


def nn_predict(model: Dict[str, Any], features: List[Any]) -> List[float]:
    x = [float(v) for v in features]
    hidden: List[float] = []
    for j in range(model["hidden"]):
        z = model["b1"][j]
        for i in range(model["input"]):
            z += x[i] * model["w1"][i][j]
        hidden.append(_sigmoid(z))

    out: List[float] = []
    for k in range(model["output"]):
        z = model["b2"][k]
        for j in range(model["hidden"]):
            z += hidden[j] * model["w2"][j][k]
        out.append(_sigmoid(z))
    return out


def nn_train_xor(epochs: int = 3000, lr: float = 0.5, seed: int = 42) -> Dict[str, Any]:
    data = [
        ([0.0, 0.0], [0.0]),
        ([0.0, 1.0], [1.0]),
        ([1.0, 0.0], [1.0]),
        ([1.0, 1.0], [0.0]),
    ]
    model = nn_create(2, 4, 1, seed)

    for _ in range(epochs):
        for x, y in data:
            hidden: List[float] = []
            for j in range(model["hidden"]):
                z = model["b1"][j]
                for i in range(model["input"]):
                    z += x[i] * model["w1"][i][j]
                hidden.append(_sigmoid(z))

            out: List[float] = []
            for k in range(model["output"]):
                z = model["b2"][k]
                for j in range(model["hidden"]):
                    z += hidden[j] * model["w2"][j][k]
                out.append(_sigmoid(z))

            delta_out = [(out[k] - y[k]) * _dsigmoid(out[k]) for k in range(model["output"])]

            delta_hidden: List[float] = []
            for j in range(model["hidden"]):
                err = sum(delta_out[k] * model["w2"][j][k] for k in range(model["output"]))
                delta_hidden.append(err * _dsigmoid(hidden[j]))

            for j in range(model["hidden"]):
                for k in range(model["output"]):
                    model["w2"][j][k] -= lr * hidden[j] * delta_out[k]
            for k in range(model["output"]):
                model["b2"][k] -= lr * delta_out[k]

            for i in range(model["input"]):
                for j in range(model["hidden"]):
                    model["w1"][i][j] -= lr * x[i] * delta_hidden[j]
            for j in range(model["hidden"]):
                model["b1"][j] -= lr * delta_hidden[j]

    return model

def _raise(err: Exception) -> None:
    raise err


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
    ap = argparse.ArgumentParser(description="Nebula ultra-advanced language runtime")
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
