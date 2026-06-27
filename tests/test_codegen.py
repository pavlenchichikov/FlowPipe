from flowpipe.codegen import generate_script
from flowpipe.pipeline import EdgeSpec, NodeSpec


def test_codegen_casttypes_real_cast():
    nodes = [NodeSpec("a", "SampleData", {"dataset": "sales", "rows": 3}),
             NodeSpec("b", "CastTypes", {"mapping": "price=float"})]
    edges = [EdgeSpec("a", "b")]
    script = generate_script(nodes, edges)
    assert "astype('float')" in script and "see params" not in script


def test_codegen_fillmissing_method():
    nodes = [NodeSpec("a", "SampleData", {"dataset": "sales", "rows": 3}),
             NodeSpec("b", "FillMissing", {"method": "ffill"})]
    script = generate_script(nodes, [EdgeSpec("a", "b")])
    assert ".ffill()" in script


def test_codegen_runs_for_simple_pipeline(tmp_path):
    nodes = [NodeSpec("a", "SampleData", {"dataset": "sales", "rows": 5}),
             NodeSpec("b", "SelectColumns", {"columns": "region, price"})]
    script = generate_script(nodes, [EdgeSpec("a", "b")])
    assert "import pandas as pd" in script
    compile(script, "<gen>", "exec")  # generated code is at least valid Python


def test_codegen_addcolumn_conditionalcolumn_runs_without_nameerror():
    # Regression for the codegen-unbound-names bug: AddColumn/ConditionalColumn
    # used to emit "lambda df: price * qty" / "np.where((price > 15), ...)"
    # where the bare column name is not bound anywhere at script-execution time.
    nodes = [
        NodeSpec("a", "SampleData", {"dataset": "sales", "rows": 5}),
        NodeSpec("b", "AddColumn", {"name": "total", "expression": "quantity * price"}),
        NodeSpec("c", "ConditionalColumn", {
            "name": "big", "condition": "total > 100",
            "value_if_true": "yes", "value_if_false": "no",
        }),
    ]
    edges = [EdgeSpec("a", "b"), EdgeSpec("b", "c")]
    script = generate_script(nodes, edges)

    namespace = {}
    exec(compile(script, "<gen>", "exec"), namespace)  # noqa: S102

    final_df = namespace["df_2"]
    assert "total" in final_df.columns
    assert "big" in final_df.columns
    assert set(final_df["big"].unique()) <= {"yes", "no"}
