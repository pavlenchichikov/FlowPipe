"""Safe vectorized expression evaluator over a DataFrame (no eval/exec).

Parses with the standard-library ast and walks a strict whitelist: column
references, literals, arithmetic/comparison/boolean operators, a few safe
builtins, and the .str/.dt accessors on a column Series. Anything else raises
SafeEvalError. Used by AddColumn and ConditionalColumn instead of eval."""
from __future__ import annotations

import ast
import operator

import pandas as pd


class SafeEvalError(Exception):
    pass


_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_CMP = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
}
_FUNCS = {"abs": abs, "round": round, "min": min, "max": max,
          "len": len, "str": str, "int": int, "float": float}
_ACCESSORS = {"str", "dt"}
# safe methods on the .str / .dt accessors
_ACC_METHODS = {
    "upper", "lower", "strip", "lstrip", "rstrip", "title", "len", "replace",
    "contains", "startswith", "endswith", "split", "extract", "slice",
    "year", "month", "day", "hour", "minute", "weekday", "dayofweek",
    "date", "normalize",
}


def _series(df: pd.DataFrame, name: str):
    if name not in df.columns:
        raise SafeEvalError(f"unknown column: {name}")
    return df[name]


def _eval(node, df):
    if isinstance(node, ast.Expression):
        return _eval(node.body, df)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return _series(df, node.id)
    if isinstance(node, ast.Subscript):
        # only df['col'] / df["col"]
        if isinstance(node.value, ast.Name) and node.value.id == "df":
            key = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                return _series(df, key.value)
        raise SafeEvalError("only df['col'] subscripting is allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left, df), _eval(node.right, df))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd | ast.USub | ast.Not):
        v = _eval(node.operand, df)
        return -v if isinstance(node.op, ast.USub) else (~v if isinstance(node.op, ast.Not) else v)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, df) for v in node.values]
        out = vals[0]
        for v in vals[1:]:
            out = (out & v) if isinstance(node.op, ast.And) else (out | v)
        return out
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP:
        return _CMP[type(node.ops[0])](_eval(node.left, df), _eval(node.comparators[0], df))
    if isinstance(node, ast.Call):
        return _eval_call(node, df)
    if isinstance(node, ast.Attribute):
        # accessor attribute read (not a call): <col>.dt.year, <col>.str.len
        attr = node.attr
        if attr in _ACC_METHODS:
            base_node = node.value
            if isinstance(base_node, ast.Attribute) and base_node.attr in _ACCESSORS:
                base_series = _eval(base_node.value, df)
                accessor = getattr(base_series, base_node.attr)
                return getattr(accessor, attr)
        raise SafeEvalError(f"attribute access not allowed: .{node.attr}")
    raise SafeEvalError(f"disallowed expression: {type(node).__name__}")


def _eval_call(node, df):
    func = node.func
    args = [_eval(a, df) for a in node.args]
    # bare whitelisted builtin: round(x), abs(x)...
    if isinstance(func, ast.Name):
        if func.id in _FUNCS:
            return _FUNCS[func.id](*args)
        raise SafeEvalError(f"function not allowed: {func.id}")
    # accessor method: <col>.str.upper(), <col>.dt.year is an attribute not call
    if isinstance(func, ast.Attribute):
        method = func.attr
        if method not in _ACC_METHODS:
            raise SafeEvalError(f"method not allowed: .{method}")
        # func.value must be <col>.str or <col>.dt
        acc = func.value
        if isinstance(acc, ast.Attribute) and acc.attr in _ACCESSORS:
            base = _eval(acc.value, df)
            accessor = getattr(base, acc.attr)
            return getattr(accessor, method)(*args)
        raise SafeEvalError("only .str/.dt accessor methods are allowed")
    raise SafeEvalError("disallowed call")


def safe_eval(expression: str, df: pd.DataFrame) -> pd.Series:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SafeEvalError(f"syntax error: {exc}") from exc
    result = _eval(tree, df)
    if not isinstance(result, pd.Series):
        # scalar (e.g. a constant) - broadcast to the frame length
        result = pd.Series([result] * len(df), index=df.index)
    return result


def check_expression(expression: str) -> str | None:
    """Parse-only validation; returns an error string or None."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        return f"syntax error: {exc}"
    try:
        # walk the tree with an empty frame; unknown-column errors are fine here,
        # we only want to reject disallowed CONSTRUCTS
        _check_nodes(tree)
    except SafeEvalError as exc:
        return str(exc)
    return None


def _check_nodes(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Lambda | ast.ListComp | ast.SetComp | ast.DictComp
                      | ast.GeneratorExp | ast.Import | ast.ImportFrom):
            raise SafeEvalError(f"disallowed construct: {type(node).__name__}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise SafeEvalError(f"dunder attribute not allowed: {node.attr}")
            if node.attr not in _ACCESSORS and node.attr not in _ACC_METHODS:
                raise SafeEvalError(f"attribute not allowed: .{node.attr}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in _FUNCS:
                raise SafeEvalError(f"function not allowed: {node.func.id}")
