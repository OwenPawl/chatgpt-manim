"""Opt-in tests execute real, isolated Manim and inspect kernel-enforced boundaries."""

import json, os, subprocess
import pytest
from chatgpt_manim.scene import SceneSpec
from chatgpt_manim.renderer import ContainerRenderer, RenderError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("MANIM_INTEGRATION") != "1",
        reason="Set MANIM_INTEGRATION=1 after building the worker",
    ),
]


async def test_real_render(tmp_path):
    spec = SceneSpec(
        title="Real render",
        resolution="480p",
        fps=15,
        objects=[{"id": "equation", "kind": "math", "text": r"e^{i\pi}+1=0"}],
        steps=[
            {"action": "write", "target": "equation", "duration": 0.4},
            {"action": "wait", "duration": 0.2},
        ],
    )
    dest = tmp_path / "out.mp4"
    await ContainerRenderer().render(spec, dest)
    r = subprocess.run(
        [
            "podman",
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--entrypoint",
            "ffprobe",
            "localhost/chatgpt-manim-worker:0.1.0",
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            "-i",
            "pipe:0",
        ],
        input=dest.read_bytes(),
        capture_output=True,
        check=True,
    )
    stream = json.loads(r.stdout)["streams"][0]
    assert stream["codec_name"] == "h264"
    assert stream["pix_fmt"] == "yuv420p"
    assert stream["height"] == 480
    assert float(stream["duration"]) >= 0.5


async def test_timeout_cleans_up(tmp_path):
    spec = SceneSpec(
        title="Timeout",
        objects=[{"id": "c", "kind": "circle"}],
        steps=[{"action": "create", "target": "c"}],
    )
    with pytest.raises(RenderError, match="timed out"):
        await ContainerRenderer(timeout=0.05).render(spec, tmp_path / "out.mp4")
    result = subprocess.run(
        ["podman", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert not any(x.startswith("manim-") for x in result.stdout.splitlines())


def test_kernel_isolation():
    renderer = ContainerRenderer()
    cmd = renderer.command("manim-isolation-test")
    cmd.insert(-1, "--entrypoint=python")
    probe = """import os,json,socket
from pathlib import Path
s=socket.socket();s.settimeout(.1)
try:s.connect(('1.1.1.1',443));network=True
except OSError:network=False
try:Path('/escape').write_text('x');root_write=True
except OSError:root_write=False
print(json.dumps({'uid':os.getuid(),'network':network,'root_write':root_write,'credentials':any(x in os.environ for x in ['MANIM_API_KEY','MANIM_SIGNING_KEY','AWS_ACCESS_KEY_ID']),'caps':next(x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('CapEff:')),'memory':Path('/sys/fs/cgroup/memory.max').read_text().strip(),'pids':Path('/sys/fs/cgroup/pids.max').read_text().strip(),'cpu':Path('/sys/fs/cgroup/cpu.max').read_text().strip()}))"""
    r = subprocess.run(cmd + ["-c", probe], capture_output=True, text=True, check=True)
    state = json.loads(r.stdout)
    assert (
        state["uid"] == 1000
        and not state["network"]
        and not state["root_write"]
        and not state["credentials"]
    )
    assert state["caps"].endswith("0000000000000000")
    assert state["memory"] == "2147483648"
    assert state["pids"] == "128"
    quota, period = map(int, state["cpu"].split())
    assert quota / period == 2
