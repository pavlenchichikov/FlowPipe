"""Pipeline scheduler - run pipelines on a cron schedule."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from flowpipe.pipeline import EdgeSpec, NodeSpec, Pipeline

SCHEDULES_DIR = "schedules"


@dataclass
class ScheduleEntry:
    id: str
    name: str
    cron: str
    pipeline: dict
    enabled: bool = True
    last_run: str | None = None
    last_status: str | None = None


class PipelineScheduler:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        self._scheduler = BackgroundScheduler()
        self._entries: dict[str, ScheduleEntry] = {}
        os.makedirs(SCHEDULES_DIR, exist_ok=True)
        self._load_entries()
        self._scheduler.start()

    def _load_entries(self):
        for fname in os.listdir(SCHEDULES_DIR):
            if fname.endswith(".json"):
                path = os.path.join(SCHEDULES_DIR, fname)
                with open(path) as f:
                    data = json.load(f)
                entry = ScheduleEntry(**data)
                self._entries[entry.id] = entry
                if entry.enabled:
                    self._add_job(entry)

    def _save_entry(self, entry: ScheduleEntry):
        path = os.path.join(SCHEDULES_DIR, f"{entry.id}.json")
        with open(path, "w") as f:
            json.dump(asdict(entry), f, indent=2)

    def _add_job(self, entry: ScheduleEntry):
        self._scheduler.add_job(
            self._run_pipeline,
            trigger=CronTrigger.from_crontab(entry.cron),
            id=entry.id,
            args=[entry.id],
            replace_existing=True,
        )

    def _run_pipeline(self, entry_id: str):
        entry = self._entries.get(entry_id)
        if not entry:
            return
        try:
            pipe_data = entry.pipeline
            nodes = [NodeSpec(**n) for n in pipe_data["nodes"]]
            edges = [EdgeSpec(**e) for e in pipe_data["edges"]]
            pipeline = Pipeline(nodes, edges)
            result = pipeline.run(self.upload_dir)
            entry.last_status = "success" if result.success else f"error: {result.error}"
        except Exception as exc:
            entry.last_status = f"error: {exc}"
        entry.last_run = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_entry(entry)

    def add(self, entry: ScheduleEntry) -> ScheduleEntry:
        self._entries[entry.id] = entry
        self._save_entry(entry)
        if entry.enabled:
            self._add_job(entry)
        return entry

    def remove(self, entry_id: str):
        if entry_id in self._entries:
            del self._entries[entry_id]
            try:
                self._scheduler.remove_job(entry_id)
            except Exception:
                pass
            path = os.path.join(SCHEDULES_DIR, f"{entry_id}.json")
            if os.path.exists(path):
                os.remove(path)

    def list_all(self) -> list[ScheduleEntry]:
        return list(self._entries.values())

    def shutdown(self):
        self._scheduler.shutdown(wait=False)
