import pandas as pd
import pytest

from flowpipe.safe_eval import SafeEvalError, check_expression, safe_eval


def _df():
    return pd.DataFrame({"price": [10, 20, 30], "qty": [1, 2, 3], "name": ["a", "bb", "ccc"]})


def test_arithmetic_on_columns():
    out = safe_eval("price * qty", _df())
    assert list(out) == [10, 40, 90]


def test_df_bracket_syntax_and_funcs():
    out = safe_eval("df['price'] + round(df['qty'] / 2)", _df())
    assert list(out) == [10 + 0, 20 + 1, 30 + 2]


def test_str_accessor():
    out = safe_eval("name.str.upper()", _df())
    assert list(out) == ["A", "BB", "CCC"]


def test_comparison_returns_bool():
    out = safe_eval("price > 15", _df())
    assert list(out) == [False, True, True]


def test_blocks_import_and_dunder():
    for bad in ["__import__('os')", "df.__class__", "().__class__.__bases__",
                "price.__reduce__()", "[x for x in price]", "lambda x: x"]:
        with pytest.raises(SafeEvalError):
            safe_eval(bad, _df())


def test_check_expression():
    assert check_expression("price * 2") is None
    assert check_expression("__import__('os')") is not None
    assert check_expression("price ** ") is not None  # syntax error


def test_dt_attribute_read():
    df = pd.DataFrame({"date": pd.to_datetime(["2024-05-01", "2025-01-15"])})
    out = safe_eval("date.dt.year", df)
    assert list(out) == [2024, 2025]


def test_dunder_attribute_still_blocked():
    with pytest.raises(SafeEvalError):
        safe_eval("price.__class__", _df())
