"""Command-line interface for FlowPipe.

Subcommands:
  serve      Run the web UI (default when no subcommand is given)
  run        Execute a pipeline JSON headless (for cron / scripts)
  nodes      List available node types
  codegen    Generate a standalone Python script from a pipeline
  validate   Check a pipeline file without running it
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

__version__ = "0.1.0"

_SUBCOMMANDS = {"serve", "run", "nodes", "codegen", "validate"}


def _load_pipeline(path: str):
    """Load a pipeline JSON file into (nodes, edges) spec lists."""
    from flowpipe.pipeline import EdgeSpec, NodeSpec

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    nodes = [NodeSpec(**n) for n in data["nodes"]]
    edges = [EdgeSpec(**e) for e in data.get("edges", [])]
    return nodes, edges


def cmd_serve(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Install with: pip install flowpipe-etl")
        return 1
    print(f"FlowPipe v{__version__}")
    print(f"Starting at http://{args.host}:{args.port}")
    uvicorn.run(
        "flowpipe.server:app", host=args.host, port=args.port, reload=args.reload
    )
    return 0


def cmd_nodes(args) -> int:
    import flowpipe.nodes  # noqa: F401  (import registers node types)
    from flowpipe.nodes.registry import all_node_specs

    specs = sorted(all_node_specs(), key=lambda s: (s["category"], s["type"]))
    if args.json:
        print(json.dumps(specs, indent=2, ensure_ascii=False))
        return 0
    category = None
    for s in specs:
        if s["category"] != category:
            category = s["category"]
            print(f"\n{category.upper()}")
        print(f"  {s['type']:<18} {s['description']}")
    print()
    return 0


def cmd_run(args) -> int:
    import flowpipe.nodes  # noqa: F401
    from flowpipe.pipeline import Pipeline

    nodes, edges = _load_pipeline(args.pipeline)
    result = Pipeline(nodes, edges).run(args.upload_dir)

    if args.json:
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False, default=str))
        return 0 if result.success else 1

    for n in result.nodes:
        if n.error:
            print(f"  [ERROR] {n.node_id} ({n.node_type}): {n.error}")
        else:
            print(
                f"  [ ok  ] {n.node_id} ({n.node_type}): "
                f"{n.rows} rows x {n.columns} cols  {n.elapsed_ms}ms"
            )
    print()
    if result.success:
        print(f"Pipeline finished in {result.total_ms}ms")
        return 0
    print(f"Pipeline failed: {result.error}")
    return 1


def cmd_codegen(args) -> int:
    import flowpipe.nodes  # noqa: F401
    from flowpipe.codegen import generate_script

    nodes, edges = _load_pipeline(args.pipeline)
    script = generate_script(nodes, edges)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"Wrote {args.output}")
    else:
        print(script, end="")
    return 0


def cmd_validate(args) -> int:
    import flowpipe.nodes  # noqa: F401
    from flowpipe.nodes.registry import get_node_class
    from flowpipe.pipeline import Pipeline

    try:
        nodes, edges = _load_pipeline(args.pipeline)
    except Exception as exc:
        print(f"Invalid pipeline file: {exc}")
        return 1

    problems = []
    ids = {n.id for n in nodes}
    for n in nodes:
        if get_node_class(n.type) is None:
            problems.append(f"unknown node type '{n.type}' (id={n.id})")
    for e in edges:
        if e.source not in ids:
            problems.append(f"edge source not found: {e.source}")
        if e.target not in ids:
            problems.append(f"edge target not found: {e.target}")
    try:
        Pipeline(nodes, edges)._topo_sort()
    except ValueError as exc:
        problems.append(str(exc))

    if problems:
        print("Invalid pipeline:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {len(nodes)} nodes, {len(edges)} edges")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flowpipe", description="FlowPipe - Visual ETL pipeline builder"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    p_serve = sub.add_parser("serve", help="Run the web UI (default)")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host to bind")
    p_serve.add_argument("--port", "-p", type=int, default=8100, help="Port to bind")
    p_serve.add_argument("--reload", action="store_true", help="Auto-reload (dev)")
    p_serve.set_defaults(func=cmd_serve)

    p_run = sub.add_parser("run", help="Execute a pipeline JSON headless")
    p_run.add_argument("pipeline", help="Path to a pipeline .json file")
    p_run.add_argument("--upload-dir", default="uploads", help="Directory for file I/O")
    p_run.add_argument("--json", action="store_true", help="Machine-readable output")
    p_run.set_defaults(func=cmd_run)

    p_nodes = sub.add_parser("nodes", help="List available node types")
    p_nodes.add_argument("--json", action="store_true", help="Machine-readable output")
    p_nodes.set_defaults(func=cmd_nodes)

    p_cg = sub.add_parser("codegen", help="Generate a standalone Python script")
    p_cg.add_argument("pipeline", help="Path to a pipeline .json file")
    p_cg.add_argument("--output", "-o", help="Write to file instead of stdout")
    p_cg.set_defaults(func=cmd_codegen)

    p_val = sub.add_parser("validate", help="Check a pipeline without running it")
    p_val.add_argument("pipeline", help="Path to a pipeline .json file")
    p_val.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Default to `serve` so `flowpipe`, `flowpipe --reload`, `flowpipe -p 9000` still work.
    if argv and argv[0] not in _SUBCOMMANDS and argv[0] not in ("-h", "--help", "--version"):
        argv = ["serve", *argv]

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        args = parser.parse_args(["serve"])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
