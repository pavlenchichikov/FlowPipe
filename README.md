# FlowPipe

**Visual ETL pipeline builder with drag-and-drop interface.**

Build data pipelines by connecting nodes on a visual canvas. Preview results at each step, export as a standalone Python script, or schedule for automated execution.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- **Drag-and-drop canvas** — visually connect source, transform, and destination nodes
- **15+ built-in nodes** — CSV, Excel, JSON, SQL sources; filter, sort, join, aggregate, rename, deduplicate, fill missing, add column, cast types; file and database destinations
- **Live preview** — run the pipeline and inspect data at each step (up to 50 rows)
- **Export to Python** — generate a standalone `.py` script from any pipeline
- **Scheduler** — set cron schedules to run pipelines automatically
- **Sample data** — built-in datasets (sales, employees, timeseries) for quick experimentation
- **Dark UI** — modern dark theme optimized for long work sessions

## Quick Start

```bash
# Install
pip install -e .

# Run
flowpipe
```

Open http://127.0.0.1:8100 in your browser.

### From source

```bash
git clone https://github.com/yourname/flowpipe.git
cd flowpipe
pip install -e ".[dev]"
flowpipe --reload
```

## Usage

### 1. Add nodes

Drag nodes from the left sidebar onto the canvas, or double-click to add them. Node categories:

| Category | Nodes |
|---|---|
| **Sources** | CSV File, Excel File, JSON File, SQL Query, Sample Data |
| **Transforms** | Filter Rows, Select Columns, Drop Columns, Rename Columns, Sort, Group & Aggregate, Join, Deduplicate, Add Column, Cast Types, Fill Missing |
| **Destinations** | Export CSV, Export Excel, Export JSON, Export to SQL |

### 2. Connect nodes

Drag from an output port (right side) to an input port (left side) to create connections. Data flows left to right.

### 3. Configure

Click any node to open its properties panel on the right. Set parameters like filenames, filter conditions, column names, etc.

### 4. Run

Click **Run Pipeline** to execute. Results appear in the bottom preview panel. Check the **Run Log** tab for per-node timing and status.

### 5. Export

Click **Export Python** to generate a standalone script. Copy to clipboard or download as `.py`.

### 6. Schedule

Click **Schedule** to set a cron expression. The pipeline will run automatically in the background.

## File Upload

Click **Upload File** in the header to upload CSV, Excel, or JSON files. Uploaded files are stored in the `uploads/` directory and can be referenced by filename in source nodes.

## API

FlowPipe exposes a REST API:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/nodes` | List available node types |
| `POST` | `/api/upload` | Upload a data file |
| `GET` | `/api/uploads` | List uploaded files |
| `POST` | `/api/run` | Execute a pipeline |
| `POST` | `/api/codegen` | Generate Python script |
| `GET` | `/api/schedules` | List scheduled pipelines |
| `POST` | `/api/schedules` | Create a schedule |
| `DELETE` | `/api/schedules/{id}` | Delete a schedule |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Run with auto-reload
flowpipe --reload
```

## Project Structure

```
flowpipe/
├── src/flowpipe/
│   ├── __main__.py       # CLI entry point
│   ├── server.py         # FastAPI application
│   ├── pipeline.py       # DAG execution engine
│   ├── codegen.py        # Python script generator
│   ├── scheduler.py      # Cron scheduler
│   ├── nodes/
│   │   ├── base.py       # Base node class
│   │   ├── registry.py   # Node auto-registration
│   │   ├── sources.py    # Data source nodes
│   │   ├── transforms.py # Transform nodes
│   │   └── destinations.py # Export nodes
│   └── static/           # Web UI (HTML/CSS/JS)
├── tests/
├── pyproject.toml
└── README.md
```

## License

MIT
