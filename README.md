# FlowPipe

Visual ETL pipeline builder. Drag-and-drop nodes on a canvas, connect them, preview results at each step — then export as a Python script or schedule to run automatically.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## What it does

You build pipelines by wiring together nodes on a canvas: sources (CSV, Excel, JSON, SQL, sample data), transforms (filter, sort, join, aggregate, deduplicate, etc.), and destinations (export to file or database). There are 15+ nodes out of the box.

Each step shows a live data preview, so you always know what's happening with your data before it moves downstream.

When you're done, you can export the whole thing as a standalone `.py` script or set a cron schedule so it runs on its own.

## Getting started

```bash
pip install -e .
flowpipe
```

Then open http://127.0.0.1:8100.

To run from source:

```bash
git clone https://github.com/pavlenchichikov/flowpipe.git
cd flowpipe
pip install -e ".[dev]"
flowpipe --reload
```

## How to use

1. **Add nodes** — drag from the sidebar or double-click
2. **Connect them** — drag from output port to input port (left to right)
3. **Configure** — click a node to set its parameters (filename, filter condition, columns, etc.)
4. **Run** — hit "Run Pipeline", check results in the preview panel
5. **Export** — generate a Python script, or set up a schedule

You can also upload CSV/Excel/JSON files via the header button — they go into `uploads/` and become available in source nodes.

## API

FlowPipe runs on FastAPI and exposes a REST API for everything: listing node types, uploading files, running pipelines, generating code, managing schedules. See `server.py` for details.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/
flowpipe --reload   # auto-reload on changes
```

## License

MIT
