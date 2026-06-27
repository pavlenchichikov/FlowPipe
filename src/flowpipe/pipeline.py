"""Core pipeline engine - DAG-based execution of node graphs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from flowpipe.nodes.registry import get_node_class


@dataclass
class NodeResult:
    node_id: str
    node_type: str
    rows: int
    columns: int
    preview: list[dict]
    elapsed_ms: float
    error: str | None = None


@dataclass
class PipelineResult:
    success: bool
    nodes: list[NodeResult]
    total_ms: float
    error: str | None = None


@dataclass
class NodeSpec:
    """Serializable specification of a single node in the pipeline."""

    id: str
    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeSpec:
    """Directed edge from source_id to target_id."""

    source: str
    target: str
    source_port: str = "output"
    target_port: str = "input"


class Pipeline:
    """Executes a DAG of ETL nodes."""

    def __init__(self, nodes: list[NodeSpec], edges: list[EdgeSpec]):
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges
        self._adj: dict[str, list[str]] = {n.id: [] for n in nodes}
        self._in_edges: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in edges:
            self._adj[e.source].append(e.target)
            self._in_edges[e.target].append(e.source)

    def _topo_sort(self) -> list[str]:
        in_degree = {nid: len(parents) for nid, parents in self._in_edges.items()}
        queue = [nid for nid, d in in_degree.items() if d == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for child in self._adj.get(nid, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if len(order) != len(self.nodes):
            raise ValueError("Pipeline contains a cycle")
        return order

    def run(self, upload_dir: str = "uploads") -> PipelineResult:
        t_start = time.perf_counter()
        order = self._topo_sort()
        outputs: dict[str, pd.DataFrame] = {}
        results: list[NodeResult] = []

        for nid in order:
            spec = self.nodes[nid]
            node_cls = get_node_class(spec.type)
            if node_cls is None:
                results.append(
                    NodeResult(nid, spec.type, 0, 0, [], 0, f"Unknown node type: {spec.type}")
                )
                return PipelineResult(
                    False, results, _elapsed(t_start), f"Unknown node: {spec.type}"
                )

            node = node_cls(spec.params, upload_dir=upload_dir)
            parents = self._in_edges.get(nid, [])
            inputs = [outputs[p] for p in parents if p in outputs]

            t_node = time.perf_counter()
            try:
                df = node.execute(inputs)
                outputs[nid] = df
                preview = df.head(50).fillna("").to_dict(orient="records")
                results.append(
                    NodeResult(nid, spec.type, len(df), len(df.columns), preview, _elapsed(t_node))
                )
            except Exception as exc:
                results.append(
                    NodeResult(nid, spec.type, 0, 0, [], _elapsed(t_node), str(exc))
                )
                return PipelineResult(False, results, _elapsed(t_start), str(exc))

        return PipelineResult(True, results, _elapsed(t_start))


def _elapsed(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
