import pandas as pd

from flowpipe.nodes.registry import get_node_class


def _node(type_name, params):
    return get_node_class(type_name)(params)


def test_csv_source_codegen_and_schema():
    import flowpipe.nodes  # noqa: F401
    n = _node("CSVSource", {"filename": "data.csv", "delimiter": ",", "encoding": "utf-8"})
    code = n.codegen([])
    assert code.startswith("pd.read_csv(") and "data.csv" in code
    assert n.output_columns([]) is None          # unknown without a probe


def test_sample_source_schema_known():
    import flowpipe.nodes  # noqa: F401
    n = _node("SampleData", {"dataset": "sales", "rows": 5})
    cols = n.output_columns([])
    assert cols and "price" in cols and "region" in cols


def test_addcolumn_uses_safe_eval_blocks_rce():
    import pytest

    import flowpipe.nodes  # noqa: F401
    from flowpipe.safe_eval import SafeEvalError
    n = _node("AddColumn", {"name": "total", "expression": "price * qty"})
    out = n.execute([pd.DataFrame({"price": [2], "qty": [3]})])
    assert out["total"].iloc[0] == 6
    bad = _node("AddColumn", {"name": "x", "expression": "__import__('os').getcwd()"})
    with pytest.raises(SafeEvalError):
        bad.execute([pd.DataFrame({"price": [1]})])


def test_filltcast_codegen_correct():
    import flowpipe.nodes  # noqa: F401
    fm = _node("FillMissing", {"method": "ffill", "columns": ""})
    assert ".ffill()" in fm.codegen(["df_0"])
    ct = _node("CastTypes", {"mapping": "price=float"})
    code = ct.codegen(["df_0"])
    assert "astype" in code and "see params" not in code


def test_selectcolumns_output_schema():
    import flowpipe.nodes  # noqa: F401
    n = _node("SelectColumns", {"columns": "a, b"})
    assert n.output_columns([["a", "b", "c"]]) == ["a", "b"]


def test_csv_destination_codegen_is_statement():
    import flowpipe.nodes  # noqa: F401
    n = _node("CSVDestination", {"filename": "out.csv", "delimiter": ","})
    code = n.codegen(["df_3"])
    assert code.startswith("df_3.to_csv(") and "out.csv" in code


def test_union_stacks_rows():
    import flowpipe.nodes  # noqa: F401
    n = _node("Union", {})
    a = pd.DataFrame({"x": [1]})
    b = pd.DataFrame({"x": [2]})
    out = n.execute([a, b])
    assert list(out["x"]) == [1, 2]


def test_conditional_column_safe():
    import flowpipe.nodes  # noqa: F401
    n = _node("ConditionalColumn", {"name": "big", "condition": "price > 15",
                                    "value_if_true": "yes", "value_if_false": "no"})
    out = n.execute([pd.DataFrame({"price": [10, 20]})])
    assert list(out["big"]) == ["no", "yes"]


def test_assert_valid_raises():
    import pytest

    import flowpipe.nodes  # noqa: F401
    n = _node("AssertValid", {"min_rows": "5"})
    with pytest.raises(AssertionError):
        n.execute([pd.DataFrame({"x": [1, 2]})])


def test_date_extract_year():
    import flowpipe.nodes  # noqa: F401
    n = _node("DateExtract", {"column": "d", "part": "year", "name": "y"})
    out = n.execute([pd.DataFrame({"d": pd.to_datetime(["2024-05-01"])})])
    assert out["y"].iloc[0] == 2024


def test_date_extract_rejects_invalid_part():
    import pytest

    import flowpipe.nodes  # noqa: F401
    n = _node("DateExtract", {"column": "d", "part": "__class__", "name": "y"})
    with pytest.raises(ValueError, match="invalid part"):
        n.execute([pd.DataFrame({"d": pd.to_datetime(["2024-05-01"])})])
    with pytest.raises(ValueError, match="invalid part"):
        n.codegen(["df_0"])


def test_string_op_rejects_invalid_op():
    import pytest

    import flowpipe.nodes  # noqa: F401
    n = _node("StringOp", {"column": "name", "op": "__import__"})
    with pytest.raises(ValueError, match="invalid op"):
        n.execute([pd.DataFrame({"name": ["a"]})])
    with pytest.raises(ValueError, match="invalid op"):
        n.codegen(["df_0"])
