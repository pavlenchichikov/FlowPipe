"""Static validation of a pipeline: structure, params, expressions, and an
optional column-schema propagation that catches bad column references early."""
from __future__ import annotations

from flowpipe.nodes.registry import get_node_class
from flowpipe.safe_eval import check_expression

_MIN_INPUTS = {"JoinTables": 2, "Union": 2}
_EXPR_PARAM = {"AddColumn": "expression", "ConditionalColumn": "condition"}


def _required(cls) -> list:
    return [f["name"] for f in cls.param_schema if f.get("required")]


def validate_pipeline(nodes, edges, probe_schema=False, upload_dir="uploads") -> list:
    import flowpipe.nodes  # noqa: F401
    problems = []
    ids = {n.id for n in nodes}
    in_edges = {n.id: [] for n in nodes}
    adj = {n.id: [] for n in nodes}
    for e in edges:
        if e.source not in ids:
            problems.append("edge source not found: %s" % e.source)
        if e.target not in ids:
            problems.append("edge target not found: %s" % e.target)
        if e.source in ids and e.target in ids:
            in_edges[e.target].append(e.source)
            adj[e.source].append(e.target)

    # node type + params + arity + expressions
    for n in nodes:
        cls = get_node_class(n.type)
        if cls is None:
            problems.append("unknown node type '%s' (id=%s)" % (n.type, n.id))
            continue
        for req in _required(cls):
            if not str(n.params.get(req, "")).strip():
                problems.append("node %s (%s): missing required param '%s'" % (n.id, n.type, req))
        need = _MIN_INPUTS.get(n.type)
        if need and len(in_edges[n.id]) < need:
            problems.append("node %s (%s): needs at least %d inputs" % (n.id, n.type, need))
        if n.type in _EXPR_PARAM:
            expr = n.params.get(_EXPR_PARAM[n.type], "")
            err = check_expression(expr) if expr else None
            if err:
                problems.append("node %s (%s): expression %s" % (n.id, n.type, err))

    # cycle
    order = _topo(nodes, in_edges, adj)
    if order is None:
        problems.append("pipeline contains a cycle")
        return problems

    if probe_schema:
        problems.extend(_check_schema(nodes, in_edges, order, upload_dir))
    return problems


def _topo(nodes, in_edges, adj):
    indeg = {n.id: len(in_edges[n.id]) for n in nodes}
    queue = [nid for nid, d in indeg.items() if d == 0]
    order = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for c in adj[nid]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    return order if len(order) == len(nodes) else None


def _probe_source(spec, upload_dir):
    import os

    import pandas as pd
    try:
        cls = get_node_class(spec.type)
        node = cls(spec.params, upload_dir=upload_dir)
        oc = node.output_columns([])
        if oc is not None:
            return oc
        if spec.type == "CSVSource":
            path = os.path.join(upload_dir, spec.params["filename"])
            return list(pd.read_csv(path, nrows=0).columns)
        if spec.type == "ExcelSource":
            path = os.path.join(upload_dir, spec.params["filename"])
            return list(pd.read_excel(path, nrows=0).columns)
        if spec.type == "JSONSource":
            path = os.path.join(upload_dir, spec.params["filename"])
            return list(pd.read_json(path).head(1).columns)
    except Exception:
        return None
    return None


def _check_schema(nodes, in_edges, order, upload_dir) -> list:
    problems = []
    node_map = {n.id: n for n in nodes}
    schemas = {}
    for nid in order:
        spec = node_map[nid]
        cls = get_node_class(spec.type)
        parents = in_edges[nid]
        if cls.category == "source":
            schemas[nid] = _probe_source(spec, upload_dir)
            continue
        in_schemas = [schemas[p] for p in parents if schemas.get(p) is not None]
        # referenced-column checks for column-naming nodes
        if in_schemas:
            ref = _referenced_columns(spec)
            known = set(in_schemas[0])
            for col in ref:
                if col not in known:
                    problems.append(
                        "node %s (%s): references unknown column '%s'" % (nid, spec.type, col))
        try:
            node = cls(spec.params, upload_dir=upload_dir)
            schemas[nid] = node.output_columns(in_schemas) if in_schemas else None
        except Exception:
            schemas[nid] = None
    return problems


def _referenced_columns(spec) -> list:
    """Columns a node names in its params (best-effort, for the common nodes)."""
    p = spec.params

    def cols(s):
        return [c.strip() for c in (s or "").split(",") if c.strip()]
    if spec.type in ("SelectColumns", "DropColumns"):
        return cols(p.get("columns", ""))
    if spec.type == "SortRows":
        return cols(p.get("columns", ""))
    if spec.type == "GroupAggregate":
        return cols(p.get("group_by", ""))
    if spec.type == "JoinTables":
        return cols(p.get("on", ""))
    return []
