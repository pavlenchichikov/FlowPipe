"""Generate standalone Python scripts from pipeline definitions.

Thin orchestrator: topo-sort the DAG and let each node emit its own pandas line
via node.codegen, so the generated code always matches node.execute."""
from __future__ import annotations

from flowpipe.nodes.registry import get_node_class
from flowpipe.pipeline import EdgeSpec, NodeSpec

_IMPORTS = """import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
"""


def _topo(nodes, edges):
    adj_in = {n.id: [] for n in nodes}
    adj_out = {n.id: [] for n in nodes}
    for e in edges:
        adj_in[e.target].append(e.source)
        adj_out[e.source].append(e.target)
    indeg = {nid: len(p) for nid, p in adj_in.items()}
    queue = [nid for nid, d in indeg.items() if d == 0]
    order = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for c in adj_out[nid]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    return order, adj_in


def _merged_params(spec):
    import flowpipe.nodes  # noqa: F401

    cls = get_node_class(spec.type)
    params = {}
    if cls:
        for field in cls.param_schema:
            if "default" in field:
                params[field["name"]] = field["default"]
    params.update(spec.params)
    return params


def generate_script(nodes: list[NodeSpec], edges: list[EdgeSpec]) -> str:
    import flowpipe.nodes  # noqa: F401

    node_map = {n.id: n for n in nodes}
    order, adj_in = _topo(nodes, edges)

    lines = ['"""Auto-generated ETL pipeline by FlowPipe."""', _IMPORTS, ""]
    var_map = {}
    for i, nid in enumerate(order):
        spec = node_map[nid]
        cls = get_node_class(spec.type)
        if cls is None:
            lines.append("# %s - unknown node type %s" % (nid, spec.type))
            continue
        node = cls(_merged_params(spec))
        parents = [var_map[p] for p in adj_in.get(nid, []) if p in var_map]
        try:
            code = node.codegen(parents)
        except NotImplementedError:
            lines.append("# df_%d = <%s> - manual implementation needed" % (i, spec.type))
            continue
        if node.category == "destination":
            lines.append(code)
        else:
            var = "df_%d" % i
            var_map[nid] = var
            lines.append("%s = %s" % (var, code))
    lines.append("")
    lines.append('print("Pipeline complete.")')
    return "\n".join(lines) + "\n"
