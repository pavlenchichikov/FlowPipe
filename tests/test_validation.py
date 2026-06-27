from flowpipe.pipeline import EdgeSpec, NodeSpec
from flowpipe.validation import validate_pipeline


def test_clean_pipeline_ok():
    nodes = [NodeSpec("a", "SampleData", {"dataset": "sales", "rows": 3}),
             NodeSpec("b", "SelectColumns", {"columns": "region, price"})]
    assert validate_pipeline(nodes, [EdgeSpec("a", "b")]) == []


def test_missing_required_param():
    nodes = [NodeSpec("a", "SampleData", {}), NodeSpec("b", "FilterRows", {})]
    probs = validate_pipeline(nodes, [EdgeSpec("a", "b")])
    assert any("condition" in p for p in probs)


def test_join_needs_two_inputs():
    nodes = [NodeSpec("a", "SampleData", {}), NodeSpec("b", "JoinTables", {"on": "id"})]
    probs = validate_pipeline(nodes, [EdgeSpec("a", "b")])
    assert any("Join" in p or "2 input" in p or "two input" in p for p in probs)


def test_bad_expression_flagged():
    nodes = [NodeSpec("a", "SampleData", {}),
             NodeSpec("b", "AddColumn", {"name": "x", "expression": "__import__('os')"})]
    probs = validate_pipeline(nodes, [EdgeSpec("a", "b")])
    assert any("expression" in p.lower() or "not allowed" in p.lower() for p in probs)


def test_schema_probe_unknown_column():
    nodes = [NodeSpec("a", "SampleData", {"dataset": "sales", "rows": 3}),
             NodeSpec("b", "SelectColumns", {"columns": "nonexistent"})]
    probs = validate_pipeline(nodes, [EdgeSpec("a", "b")], probe_schema=True)
    assert any("nonexistent" in p for p in probs)
