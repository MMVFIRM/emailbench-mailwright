"""Small OData $filter / $orderby evaluator for the mock API.

Supports: eq ne gt ge lt le, and/or/not, parentheses, contains/startswith/endswith(field,'x'),
string/number/bool/null/datetime literals, slash or dot field paths
(from/emailAddress/address), and collection lambdas `categories/any(c:c eq 'X')`
and `toRecipients/any(r:r/emailAddress/address eq 'x')`.
String comparisons are case-insensitive (as in Exchange).
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r"""
    (?P<ws>\s+)|
    (?P<str>'(?:[^']|'')*')|
    (?P<dt>\d{4}-\d{2}-\d{2}T[0-9:.]+Z?)|
    (?P<num>-?\d+(?:\.\d+)?)|
    (?P<lp>\()|(?P<rp>\))|(?P<comma>,)|(?P<colon>:)|
    (?P<ident>[A-Za-z_@$][A-Za-z0-9_./@$]*)
""", re.X)


class ODataError(ValueError):
    pass


def tokenize(s):
    pos, out = 0, []
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ODataError(f"Unexpected character at position {pos}: {s[pos:pos+15]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        val = m.group(kind)
        if kind == "str":
            val = val[1:-1].replace("''", "'")
        out.append((kind, val))
    return out


def get_path(obj, path):
    parts = [p for p in re.split(r"[/.]", path) if p]
    cur = obj
    for p in parts:
        if isinstance(cur, dict):
            # case-insensitive key lookup
            if p in cur:
                cur = cur[p]
            else:
                low = {k.lower(): k for k in cur}
                if p.lower() in low:
                    cur = cur[low[p.lower()]]
                else:
                    return None
        else:
            return None
    return cur


def _norm(v):
    if isinstance(v, str):
        return v.lower()
    return v


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        return self.t[self.i + k] if self.i + k < len(self.t) else (None, None)

    def take(self, kind=None, val=None):
        tok = self.peek()
        if kind and tok[0] != kind:
            raise ODataError(f"Expected {kind} but found {tok[1]!r}")
        if val and (tok[1] or "").lower() != val:
            raise ODataError(f"Expected {val!r} but found {tok[1]!r}")
        self.i += 1
        return tok

    def parse(self):
        e = self.or_()
        if self.i != len(self.t):
            raise ODataError(f"Unexpected token {self.peek()[1]!r}")
        return e

    def or_(self):
        e = self.and_()
        while self.peek()[0] == "ident" and self.peek()[1].lower() == "or":
            self.take()
            r = self.and_()
            e = ("or", e, r)
        return e

    def and_(self):
        e = self.not_()
        while self.peek()[0] == "ident" and self.peek()[1].lower() == "and":
            self.take()
            r = self.not_()
            e = ("and", e, r)
        return e

    def not_(self):
        if self.peek()[0] == "ident" and self.peek()[1].lower() == "not":
            self.take()
            return ("not", self.not_())
        return self.cmp()

    def cmp(self):
        left = self.atom()
        tok = self.peek()
        if tok[0] == "ident" and tok[1].lower() in ("eq", "ne", "gt", "ge", "lt", "le"):
            self.take()
            right = self.atom()
            return ("cmp", tok[1].lower(), left, right)
        return left

    def atom(self):
        kind, val = self.peek()
        if kind == "lp":
            self.take()
            e = self.or_()
            self.take("rp")
            return e
        if kind in ("str", "dt"):
            self.take()
            return ("lit", val)
        if kind == "num":
            self.take()
            return ("lit", float(val) if "." in val else int(val))
        if kind == "ident":
            low = val.lower()
            if low in ("true", "false"):
                self.take()
                return ("lit", low == "true")
            if low == "null":
                self.take()
                return ("lit", None)
            if low in ("contains", "startswith", "endswith", "substringof") and self.peek(1)[0] == "lp":
                self.take()
                self.take("lp")
                a = self.or_()
                self.take("comma")
                b = self.or_()
                self.take("rp")
                if low == "substringof":
                    a, b = b, a
                return ("fn", low, a, b)
            if low in ("tolower", "toupper") and self.peek(1)[0] == "lp":
                self.take(); self.take("lp"); a = self.or_(); self.take("rp")
                return a
            self.take()
            # lambda any/all: path/any(x:expr)
            m = re.match(r"^(.*)/(any|all)$", val, re.I)
            if m and self.peek()[0] == "lp":
                self.take("lp")
                if self.peek()[0] == "rp":
                    self.take()
                    return ("any_nonempty", m.group(1))
                var = self.take("ident")[1]
                self.take("colon")
                body = self.or_()
                self.take("rp")
                return ("lambda", m.group(2).lower(), m.group(1), var, body)
            return ("path", val)
        raise ODataError(f"Unexpected token {val!r}")


def compile_filter(expr: str):
    if not expr or not expr.strip():
        return lambda obj: True
    tree = Parser(tokenize(expr)).parse()
    return lambda obj: bool(_eval(tree, obj, {}))


def _eval(n, obj, env):
    op = n[0]
    if op == "lit":
        return n[1]
    if op == "path":
        p = n[1]
        head = re.split(r"[/.]", p)[0]
        if head in env:
            rest = p[len(head):].lstrip("/.")
            return get_path(env[head], rest) if rest else env[head]
        return get_path(obj, p)
    if op == "and":
        return _eval(n[1], obj, env) and _eval(n[2], obj, env)
    if op == "or":
        return _eval(n[1], obj, env) or _eval(n[2], obj, env)
    if op == "not":
        return not _eval(n[1], obj, env)
    if op == "fn":
        a, b = _eval(n[2], obj, env), _eval(n[3], obj, env)
        if a is None or b is None:
            return False
        a, b = str(a).lower(), str(b).lower()
        return {"contains": b in a, "substringof": b in a, "startswith": a.startswith(b), "endswith": a.endswith(b)}[n[1]]
    if op == "cmp":
        a, b = _norm(_eval(n[2], obj, env)), _norm(_eval(n[3], obj, env))
        if n[1] == "eq":
            return a == b
        if n[1] == "ne":
            return a != b
        if a is None or b is None:
            return False
        try:
            return {"gt": a > b, "ge": a >= b, "lt": a < b, "le": a <= b}[n[1]]
        except TypeError:
            return str(a) > str(b) if n[1] == "gt" else str(a) >= str(b) if n[1] == "ge" else str(a) < str(b) if n[1] == "lt" else str(a) <= str(b)
    if op == "any_nonempty":
        v = get_path(obj, n[1])
        return bool(v)
    if op == "lambda":
        kind, path, var, body = n[1], n[2], n[3], n[4]
        coll = get_path(obj, path) or []
        res = [_eval(body, obj, {**env, var: item}) for item in coll]
        return any(res) if kind == "any" else all(res)
    raise ODataError(f"bad node {op}")


def order_key_fn(order_by: str):
    """Returns (key_fn, reverse)."""
    if not order_by:
        return (lambda o: get_path(o, "receivedDateTime") or ""), True
    parts = order_by.strip().split()
    field = parts[0]
    rev = len(parts) > 1 and parts[1].lower() == "desc"

    def k(o):
        v = get_path(o, field)
        if v is None:
            return (0, "")
        if isinstance(v, bool):
            return (1, int(v))
        if isinstance(v, (int, float)):
            return (1, v)
        return (1, str(v).lower())
    return k, rev
