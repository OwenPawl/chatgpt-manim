"""Disposable OCI workers. The server never imports Manim or executes scene source."""

import asyncio
import uuid
from pathlib import Path
from .scene import SceneSpec


class RenderError(RuntimeError):
    pass


class ContainerRenderer:
    def __init__(
        self,
        runtime="podman",
        image="localhost/chatgpt-manim-worker:0.1.0",
        timeout=180,
    ):
        self.runtime = runtime
        self.image = image
        self.timeout = timeout

    def command(self, name):
        return [
            self.runtime,
            "run",
            "--rm",
            "--name",
            name,
            "-i",
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=1000:1000",
            "--cpus=2",
            "--memory=2g",
            "--memory-swap=2g",
            "--pids-limit=128",
            "--ulimit=nofile=256:256",
            "--ulimit=fsize=67108864:67108864",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=128m,mode=1777",
            "--tmpfs=/work:rw,noexec,nosuid,size=512m,mode=1777",
            self.image,
        ]

    async def render(self, spec: SceneSpec, destination: Path):
        name = "manim-" + uuid.uuid4().hex
        process = await asyncio.create_subprocess_exec(
            *self.command(name),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            output, error = await asyncio.wait_for(
                process.communicate(spec.model_dump_json().encode()), self.timeout
            )
            if process.returncode or not output:
                raise RenderError(
                    "Render failed: " + error.decode(errors="replace")[-3000:]
                )
            if len(output) > 32 * 1024 * 1024 or output[4:8] != b"ftyp":
                raise RenderError("Worker returned invalid or oversized MP4")
            tmp = destination.with_suffix(".partial")
            tmp.write_bytes(output)
            tmp.replace(destination)
        except asyncio.TimeoutError as e:
            raise RenderError(f"Render timed out after {self.timeout} seconds") from e
        finally:
            # Killing the CLI alone can leave a container alive. Explicitly remove by an unguessable name.
            cleanup = await asyncio.create_subprocess_exec(
                self.runtime,
                "rm",
                "-f",
                name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(cleanup.wait(), 10)
            except asyncio.TimeoutError:
                cleanup.kill()
                await cleanup.wait()
            if process.returncode is None:
                process.kill()
                await process.wait()
