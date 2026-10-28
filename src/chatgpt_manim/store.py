"""Durable owner-scoped scenes, content-addressed caching, quotas, and revision lineage."""

import asyncio
import hashlib
from pathlib import Path
import sqlite3
import time
import uuid
from .renderer import RenderError


class Store:
    def __init__(
        self,
        path: Path,
        renderer,
        max_jobs=100,
        max_pending=8,
        daily_quota=30,
        retention_days=7,
    ):
        self.path = path
        path.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path / "jobs.sqlite", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,owner TEXT,hash TEXT,spec TEXT,status TEXT,error TEXT,parent TEXT,instructions TEXT,created REAL)"
        )
        self.db.execute(
            "UPDATE jobs SET status='failed',error='Service restarted during render; retry the scene.' WHERE status IN ('queued','rendering')"
        )
        self.db.commit()
        self.renderer = renderer
        self.max_jobs = max_jobs
        self.max_pending = max_pending
        self.daily_quota = daily_quota
        self.retention = retention_days * 86400
        self.tasks = set()
        self.semaphore = asyncio.Semaphore(1)

    def get(self, owner, job_id):
        row = self.db.execute(
            "SELECT * FROM jobs WHERE id=? AND owner=?", (job_id, owner)
        ).fetchone()
        if row is None:
            raise ValueError("Animation not found")
        return dict(row)

    def purge(self):
        expired = self.db.execute(
            "SELECT id FROM jobs WHERE created<? AND status NOT IN ('queued','rendering')",
            (time.time() - self.retention,),
        ).fetchall()
        for r in expired:
            (self.path / (r["id"] + ".mp4")).unlink(missing_ok=True)
        self.db.execute(
            "DELETE FROM jobs WHERE created<? AND status NOT IN ('queued','rendering')",
            (time.time() - self.retention,),
        )
        self.db.commit()

    def submit(self, owner, spec, parent=None, instructions=""):
        self.purge()
        canonical = spec.model_dump_json()
        digest = hashlib.sha256(
            ("renderer-v1-manim-0.22.1:" + canonical).encode()
        ).hexdigest()
        cached = self.db.execute(
            "SELECT * FROM jobs WHERE owner=? AND hash=? AND status IN ('queued','rendering','ready') ORDER BY created DESC LIMIT 1",
            (owner, digest),
        ).fetchone()
        if cached and (
            cached["status"] != "ready"
            or (self.path / (cached["id"] + ".mp4")).exists()
        ):
            return dict(cached), True
        count = self.db.execute("SELECT count(*) FROM jobs").fetchone()[0]
        pending = self.db.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('queued','rendering')"
        ).fetchone()[0]
        daily = self.db.execute(
            "SELECT count(*) FROM jobs WHERE owner=? AND created>?",
            (owner, time.time() - 86400),
        ).fetchone()[0]
        if count >= self.max_jobs:
            raise ValueError(
                "Storage quota reached; wait for retention cleanup or contact the operator"
            )
        if pending >= self.max_pending:
            raise ValueError("Render queue is full; retry later")
        if daily >= self.daily_quota:
            raise ValueError("Daily render quota reached")
        job_id = uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
            (
                job_id,
                owner,
                digest,
                canonical,
                "queued",
                None,
                parent,
                instructions,
                time.time(),
            ),
        )
        self.db.commit()
        task = asyncio.create_task(self.run(job_id, spec))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return self.get(owner, job_id), False

    async def run(self, job_id, spec):
        async with self.semaphore:
            self.db.execute("UPDATE jobs SET status='rendering' WHERE id=?", (job_id,))
            self.db.commit()
            try:
                await self.renderer.render(spec, self.path / (job_id + ".mp4"))
                self.db.execute("UPDATE jobs SET status='ready' WHERE id=?", (job_id,))
            except Exception as e:
                message = (
                    str(e)
                    if isinstance(e, RenderError)
                    else "Internal render failure; contact the operator."
                )
                self.db.execute(
                    "UPDATE jobs SET status='failed',error=? WHERE id=?",
                    (message[:3500], job_id),
                )
            finally:
                self.db.commit()

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.db.close()
