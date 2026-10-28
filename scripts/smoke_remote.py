"""Exercise the configured HTTP server without printing credentials or signed media URLs."""

import json, time, hmac, hashlib
from pathlib import Path
import httpx

config = dict(
    line.split("=", 1)
    for line in Path(".env").read_text().splitlines()
    if line and not line.startswith("#")
)
base = config["MANIM_BASE_URL"]
headers = {
    "Authorization": "Bearer " + config["MANIM_API_KEY"],
    "Accept": "application/json, text/event-stream",
}
with httpx.Client(timeout=30) as client:
    assert client.post(base + "/mcp").status_code == 401

    def rpc(method, params):
        r = client.post(
            base + "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        r.raise_for_status()
        return r.json()["result"]

    init = rpc(
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "smoke", "version": "1"},
        },
    )
    print("HTTPS initialization:", init["serverInfo"]["name"])
    result = rpc(
        "tools/call",
        {
            "name": "render_animation",
            "arguments": {
                "spec": json.loads(Path("examples/fourier.json").read_text())
            },
        },
    )
    job = result["structuredContent"]["id"]
    for _ in range(90):
        result = rpc(
            "tools/call", {"name": "get_animation", "arguments": {"animation_id": job}}
        )
        if result["structuredContent"]["status"] in ("ready", "failed"):
            break
        time.sleep(2)
    assert result["structuredContent"]["status"] == "ready", result
    r = client.get(result["_meta"]["media_url"], headers={"Range": "bytes=0-63"})
    assert r.status_code == 206
    print("HTTPS real render ready; range streaming verified. Animation:", job)
    expires = int(time.time()) + 900
    sig = hmac.new(
        config["MANIM_SIGNING_KEY"].encode(),
        f"preview:{job}:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    Path(".agent").mkdir(exist_ok=True)
    Path(".agent/preview-url.txt").write_text(
        f"{base}/preview/{job}?expires={expires}&signature={sig}"
    )
    Path(".agent/smoke-result.json").write_text(
        json.dumps({"id": job, "status": "ready", "base_url": base})
    )
    revision = rpc(
        "tools/call",
        {
            "name": "revise_animation",
            "arguments": {
                "animation_id": job,
                "instructions": "Make the animation twice as slow.",
                "pacing": 2,
            },
        },
    )
    revision_id = revision["structuredContent"]["id"]
    assert revision["structuredContent"]["parent"] == job
    for _ in range(90):
        revision = rpc(
            "tools/call",
            {"name": "get_animation", "arguments": {"animation_id": revision_id}},
        )
        if revision["structuredContent"]["status"] in ("ready", "failed"):
            break
        time.sleep(2)
    assert revision["structuredContent"]["status"] == "ready", revision
    repeated = rpc(
        "tools/call",
        {
            "name": "revise_animation",
            "arguments": {
                "animation_id": job,
                "instructions": "Make the animation twice as slow.",
                "pacing": 2,
            },
        },
    )
    assert (
        repeated["structuredContent"]["cached"]
        and repeated["structuredContent"]["id"] == revision_id
    )
    import subprocess

    video = client.get(revision["_meta"]["media_url"])
    video.raise_for_status()
    probe = subprocess.run(
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
        input=video.content,
        capture_output=True,
        check=True,
    )
    duration = float(json.loads(probe.stdout)["streams"][0]["duration"])
    expected = (
        sum(step["duration"] for step in revision["structuredContent"]["spec"]["steps"])
        * 2
    )
    assert abs(duration - expected) < 0.2, (duration, expected)
    print(
        "Remote revision, cache reuse and doubled MP4 duration verified:",
        duration,
        "seconds",
    )
    Path(".agent/revision-result.json").write_text(
        json.dumps(
            {
                "id": revision_id,
                "parent": job,
                "duration": duration,
                "cached_reuse": True,
            }
        )
    )
