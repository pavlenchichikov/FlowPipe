# FlowPipe

A visual ETL builder. Wire nodes together on a canvas, preview the data at each
step, then export the result as a Python script or run it on a cron schedule.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Install

```bash
pip install -e .
flowpipe          # serves http://127.0.0.1:8100
```

For development use `pip install -e ".[dev]"` and `flowpipe serve --reload`.

## Nodes

15+ nodes in three groups: sources (CSV, Excel, JSON, SQL, sample data),
transforms (filter, sort, join, aggregate, deduplicate), and destinations
(file or database). Drag from the sidebar, connect output ports to input ports,
click a node to set its params, then run. Uploaded files land in `uploads/` and
show up in source nodes.

## Command line

Pipelines are plain JSON (`{"nodes": [...], "edges": [...]}`), so they run without
the UI - useful for cron and CI.

```bash
flowpipe nodes                       # list node types
flowpipe validate pipeline.json      # check without running
flowpipe run pipeline.json           # execute; non-zero exit on failure
flowpipe codegen pipeline.json -o out.py
```

`--json` on `run` and `nodes` gives machine-readable output. See
`examples/sales_report.json` for the format.

## API

A FastAPI REST API covers everything the UI does - node types, uploads, runs,
codegen, schedules. See `server.py`.

## License

MIT
