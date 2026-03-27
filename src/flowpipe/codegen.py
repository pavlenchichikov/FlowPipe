"""Generate standalone Python scripts from pipeline definitions."""

from __future__ import annotations

from flowpipe.pipeline import EdgeSpec, NodeSpec

_IMPORTS = """import pandas as pd
from sqlalchemy import create_engine, text
"""

_SOURCE_TEMPLATES: dict[str, str] = {
    "CSVSource": 'pd.read_csv({filename!r}, delimiter={delimiter!r}, encoding={encoding!r})',
    "ExcelSource": 'pd.read_excel({filename!r}, sheet_name={sheet_name!r})',
    "JSONSource": 'pd.read_json({filename!r}, orient={orient!r})',
    "SQLSource": 'pd.read_sql(text({query!r}), create_engine({connection_string!r}).connect())',
    "SampleData": 'pd.DataFrame({{"x": range({rows})}})',
}

_DEST_TEMPLATES: dict[str, str] = {
    "CSVDestination": '{input}.to_csv({filename!r}, sep={delimiter!r}, index=False)',
    "ExcelDestination": '{input}.to_excel({filename!r}, sheet_name={sheet_name!r}, index=False)',
    "JSONDestination": '{input}.to_json({filename!r}, orient={orient!r}, indent=2, force_ascii=False)',
    "SQLDestination": '{input}.to_sql({table_name!r}, create_engine({connection_string!r}), if_exists={if_exists!r}, index=False)',
}

_TRANSFORM_TEMPLATES: dict[str, str] = {
    "FilterRows": '{input}.query({condition!r})',
    "SelectColumns": '{input}[[{cols}]]',
    "DropColumns": '{input}.drop(columns=[{cols}])',
    "SortRows": '{input}.sort_values([{cols}], ascending={ascending})',
    "Deduplicate": '{input}.drop_duplicates()',
    "AddColumn": '{input}.assign(**{{{name!r}: lambda df: {expression}}})',
    "FillMissing": '{input}.fillna({value!r})',
    "GroupAggregate": '{input}.groupby([{group_cols}], as_index=False).agg({agg_dict})',
    "RenameColumns": '{input}.rename(columns={mapping})',
    "CastTypes": '{input}  # cast types — see params',
    "JoinTables": '{input_0}.merge({input_1}, on=[{on_cols}], how={how!r})',
}


def generate_script(nodes: list[NodeSpec], edges: list[EdgeSpec]) -> str:
    node_map = {n.id: n for n in nodes}
    adj_in: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in edges:
        adj_in[e.target].append(e.source)

    in_degree = {nid: len(parents) for nid, parents in adj_in.items()}
    queue = [nid for nid, d in in_degree.items() if d == 0]
    order = []
    adj_out: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in edges:
        adj_out[e.source].append(e.target)
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for child in adj_out.get(nid, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    lines = ['"""Auto-generated ETL pipeline by FlowPipe."""\n', _IMPORTS, ""]
    var_map: dict[str, str] = {}

    for i, nid in enumerate(order):
        spec = node_map[nid]
        var = f"df_{i}"
        var_map[nid] = var
        parents = adj_in.get(nid, [])
        p = spec.params

        if spec.type in _SOURCE_TEMPLATES:
            tpl = _SOURCE_TEMPLATES[spec.type]
            expr = tpl.format(**p)
            lines.append(f"{var} = {expr}")

        elif spec.type in _DEST_TEMPLATES:
            tpl = _DEST_TEMPLATES[spec.type]
            input_var = var_map.get(parents[0], "df") if parents else "df"
            expr = tpl.format(input=input_var, **p)
            lines.append(expr)

        elif spec.type == "JoinTables":
            in0 = var_map.get(parents[0], "df") if len(parents) > 0 else "df"
            in1 = var_map.get(parents[1], "df") if len(parents) > 1 else "df"
            on_cols = ", ".join(f"'{c.strip()}'" for c in p.get("on", "").split(",") if c.strip())
            lines.append(f"{var} = {in0}.merge({in1}, on=[{on_cols}], how={p.get('how', 'inner')!r})")

        elif spec.type in _TRANSFORM_TEMPLATES:
            input_var = var_map.get(parents[0], "df") if parents else "df"
            tpl = _TRANSFORM_TEMPLATES[spec.type]

            if spec.type == "SelectColumns":
                cols = ", ".join(f"'{c.strip()}'" for c in p.get("columns", "").split(",") if c.strip())
                expr = tpl.format(input=input_var, cols=cols)
            elif spec.type == "DropColumns":
                cols = ", ".join(f"'{c.strip()}'" for c in p.get("columns", "").split(",") if c.strip())
                expr = tpl.format(input=input_var, cols=cols)
            elif spec.type == "SortRows":
                cols = ", ".join(f"'{c.strip()}'" for c in p.get("columns", "").split(",") if c.strip())
                asc = p.get("ascending", "ascending") == "ascending"
                expr = tpl.format(input=input_var, cols=cols, ascending=asc)
            elif spec.type == "GroupAggregate":
                gc = ", ".join(f"'{c.strip()}'" for c in p.get("group_by", "").split(",") if c.strip())
                agg = {}
                for line in p.get("aggregations", "").strip().splitlines():
                    if "=" in line:
                        col, func = line.split("=", 1)
                        agg[col.strip()] = func.strip()
                expr = tpl.format(input=input_var, group_cols=gc, agg_dict=repr(agg))
            elif spec.type == "RenameColumns":
                mapping = {}
                for line in p.get("mapping", "").strip().splitlines():
                    if "=" in line:
                        old, new = line.split("=", 1)
                        mapping[old.strip()] = new.strip()
                expr = tpl.format(input=input_var, mapping=repr(mapping))
            else:
                expr = tpl.format(input=input_var, **p)

            lines.append(f"{var} = {expr}")
        else:
            lines.append(f"# {var} = <{spec.type}> — manual implementation needed")

    lines.append("")
    lines.append('print("Pipeline complete.")')
    return "\n".join(lines) + "\n"
