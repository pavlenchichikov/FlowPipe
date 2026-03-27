"""FastAPI server — REST API and static file serving."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from flowpipe.codegen import generate_script
from flowpipe.nodes.registry import all_node_specs
from flowpipe.pipeline import EdgeSpec, NodeSpec, Pipeline
from flowpipe.scheduler import PipelineScheduler, ScheduleEntry

UPLOAD_DIR = "uploads"
STATIC_DIR = Path(__file__).parent / "static"

scheduler: PipelineScheduler | None = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    global scheduler
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    scheduler = PipelineScheduler(upload_dir=UPLOAD_DIR)
    yield
    scheduler.shutdown()


app = FastAPI(title="FlowPipe", version="0.1.0", lifespan=lifespan)


# ── API routes ──────────────────────────────────────────────────

@app.get("/api/nodes")
async def list_nodes():
    return all_node_specs()


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_name = file.filename.replace("..", "").replace("/", "_").replace("\\", "_")
    path = os.path.join(UPLOAD_DIR, safe_name)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return {"filename": safe_name, "size": len(content)}


@app.get("/api/uploads")
async def list_uploads():
    if not os.path.exists(UPLOAD_DIR):
        return []
    return sorted(os.listdir(UPLOAD_DIR))


@app.post("/api/run")
async def run_pipeline(payload: dict[str, Any]):
    try:
        nodes = [NodeSpec(**n) for n in payload["nodes"]]
        edges = [EdgeSpec(**e) for e in payload.get("edges", [])]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(UPLOAD_DIR)
        return asdict(result)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.post("/api/codegen")
async def codegen(payload: dict[str, Any]):
    try:
        nodes = [NodeSpec(**n) for n in payload["nodes"]]
        edges = [EdgeSpec(**e) for e in payload.get("edges", [])]
        script = generate_script(nodes, edges)
        return {"script": script}
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


# ── Schedule routes ─────────────────────────────────────────────

@app.get("/api/schedules")
async def list_schedules():
    return [asdict(e) for e in scheduler.list_all()]


@app.post("/api/schedules")
async def create_schedule(payload: dict[str, Any]):
    entry = ScheduleEntry(
        id=payload.get("id", str(uuid.uuid4())[:8]),
        name=payload["name"],
        cron=payload["cron"],
        pipeline=payload["pipeline"],
        enabled=payload.get("enabled", True),
    )
    scheduler.add(entry)
    return asdict(entry)


@app.delete("/api/schedules/{entry_id}")
async def delete_schedule(entry_id: str):
    scheduler.remove(entry_id)
    return {"ok": True}


# ── Static files ────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
