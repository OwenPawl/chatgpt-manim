import asyncio, time
import pytest
from starlette.testclient import TestClient
from chatgpt_manim.auth import Auth
from chatgpt_manim.server import Service, create_app
from chatgpt_manim.store import Store
from chatgpt_manim.renderer import RenderError, ContainerRenderer
from chatgpt_manim.scene import SceneSpec


class FakeRenderer:
    async def render(self, spec, path):
        path.write_bytes(b"\x00\x00\x00\x18ftyp" + b"x" * 200)


@pytest.fixture
def spec():
    return SceneSpec(
        title="Test",
        objects=[{"id": "a", "kind": "circle"}],
        steps=[{"action": "create", "target": "a", "duration": 0.2}],
    )


@pytest.fixture
def service(tmp_path):
    return Service(
        Store(tmp_path, FakeRenderer()),
        Auth("http://testserver", "x" * 40),
        "s" * 40,
        preview=True,
    )


def rpc(c, name, args=None, id=2):
    r = c.post(
        "/mcp",
        headers={
            "Authorization": "Bearer " + "x" * 40,
            "Accept": "application/json, text/event-stream",
        },
        json={"jsonrpc": "2.0", "id": id, "method": name, "params": args or {}},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_discovery_and_mcp(service):
    with TestClient(create_app(service)) as c:
        assert c.post("/mcp").status_code == 401
        assert "resource_metadata" not in c.post("/mcp").headers["www-authenticate"]
        assert (
            c.post("/mcp", headers={"Authorization": "Bearer wrong"}).status_code == 401
        )
        assert c.get("/.well-known/oauth-protected-resource").status_code == 404
        init = rpc(
            c,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1"},
            },
        )
        assert init["result"]["serverInfo"]["name"] == "Manim Animation"
        tools = rpc(c, "tools/list")["result"]["tools"]
        assert len(tools) == 4
        render = next(t for t in tools if t["name"] == "render_animation")
        assert render["_meta"]["ui"]["resourceUri"].startswith("ui://")
        assert render["annotations"]["destructiveHint"] is False
        assert render["outputSchema"]["properties"]["status"]["enum"] == [
            "queued",
            "rendering",
            "ready",
            "failed",
        ]
        ui = rpc(c, "resources/read", {"uri": "ui://manim/player-v1.html"})["result"][
            "contents"
        ][0]
        assert ui["mimeType"] == "text/html;profile=mcp-app"
        assert "ui/initialize" in ui["text"]
        assert ui["_meta"]["ui"]["csp"]["resourceDomains"] == ["http://testserver"]


def test_mcp_render_revision_and_invalid(service, spec):
    with TestClient(create_app(service)) as c:
        rpc(
            c,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1"},
            },
        )
        first = rpc(
            c,
            "tools/call",
            {"name": "render_animation", "arguments": {"spec": spec.model_dump()}},
        )["result"]
        assert not first.get("isError")
        job = first["structuredContent"]["id"]
        for _ in range(10):
            result = rpc(
                c,
                "tools/call",
                {"name": "get_animation", "arguments": {"animation_id": job}},
            )["result"]
            if result["structuredContent"]["status"] == "ready":
                break
        assert result["structuredContent"]["status"] == "ready"
        media = c.get(result["_meta"]["media_url"], headers={"Range": "bytes=0-7"})
        assert media.status_code == 206
        assert len(media.content) == 8
        assert (
            c.get(
                result["_meta"]["media_url"].replace("signature=", "signature=bad")
            ).status_code
            == 403
        )
        assert c.get(service.url(job, "preview")).status_code == 200
        revision = rpc(
            c,
            "tools/call",
            {
                "name": "revise_animation",
                "arguments": {
                    "animation_id": job,
                    "instructions": "Twice as slow",
                    "pacing": 2,
                },
            },
        )["result"]["structuredContent"]
        assert revision["parent"] == job
        assert revision["spec"]["pacing"] == 2
        bad = rpc(
            c,
            "tools/call",
            {
                "name": "render_animation",
                "arguments": {"spec": {"source": "import os"}},
            },
        )
        assert bad.get("error") or bad["result"]["isError"]
        absent = rpc(
            c,
            "tools/call",
            {"name": "get_animation", "arguments": {"animation_id": "a" * 32}},
        )["result"]
        assert absent["isError"]


async def test_cache_owner_and_quota(tmp_path, spec):
    store = Store(tmp_path, FakeRenderer(), daily_quota=1)
    row, cache = store.submit("a", spec)
    assert not cache
    await asyncio.gather(*store.tasks)
    same, cache = store.submit("a", spec)
    assert cache and same["id"] == row["id"]
    with pytest.raises(ValueError):
        store.get("b", row["id"])
    different = spec.model_copy(update={"title": "Different"})
    with pytest.raises(ValueError, match="quota"):
        store.submit("a", different)
    other, cache = store.submit("b", spec)
    assert not cache and other["id"] != row["id"]
    await store.close()


async def test_failure_reporting(tmp_path, spec):
    class Fail:
        async def render(self, *args):
            raise RenderError("Useful render failure")

    store = Store(tmp_path, Fail())
    row, _ = store.submit("a", spec)
    await asyncio.gather(*store.tasks)
    assert store.get("a", row["id"])["error"] == "Useful render failure"
    await store.close()


def test_expired_signature(service):
    from starlette.requests import Request

    t = int(time.time()) - 1
    r = Request(
        {
            "type": "http",
            "path_params": {"job_id": "a" * 32},
            "query_string": f"expires={t}&signature={service.signature('a' * 32, t, 'media')}".encode(),
            "headers": [],
        }
    )
    with pytest.raises(ValueError):
        service.check(r, "media")


def test_worker_limits():
    command = ContainerRenderer().command("test")
    for flag in [
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=1000:1000",
        "--cpus=2",
        "--memory=2g",
        "--pids-limit=128",
    ]:
        assert flag in command
    assert not any(x.startswith(("-v", "--volume", "--mount")) for x in command)


async def test_fail_closed_auth():
    with pytest.raises(ValueError):
        Auth("http://localhost")
    auth = Auth("http://localhost", "x" * 40)
    with pytest.raises(ValueError):
        await auth.identity("Bearer bad")
    assert await auth.identity("Bearer " + "x" * 40) == "personal"


def test_rate_limit_and_origin(service):
    with TestClient(create_app(service)) as c:
        assert (
            c.post(
                "/mcp",
                headers={
                    "Authorization": "Bearer " + "x" * 40,
                    "Origin": "https://evil.example",
                },
            ).status_code
            == 403
        )
        for _ in range(120):
            c.post("/mcp", headers={"Authorization": "Bearer " + "x" * 40}, json={})
        assert (
            c.post(
                "/mcp", headers={"Authorization": "Bearer " + "x" * 40}, json={}
            ).status_code
            == 429
        )


def test_persist_and_restart(tmp_path, spec):
    first = Store(tmp_path, FakeRenderer())
    first.db.execute(
        "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "a" * 32,
            "owner",
            "hash",
            spec.model_dump_json(),
            "rendering",
            None,
            None,
            "",
            time.time(),
        ),
    )
    first.db.commit()
    first.db.close()
    second = Store(tmp_path, FakeRenderer())
    assert second.get("owner", "a" * 32)["status"] == "failed"
    second.db.close()


async def test_oauth_signature_audience_expiry(monkeypatch):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = Auth(
        "https://service.example",
        issuer="https://issuer.example/",
        audience="https://service.example/mcp",
        jwks_url="https://issuer.example/jwks",
    )
    from types import SimpleNamespace

    signing = SimpleNamespace(key=key.public_key())
    monkeypatch.setattr(auth.jwks, "get_signing_key_from_jwt", lambda token: signing)
    claims = {
        "iss": auth.issuer,
        "aud": auth.audience,
        "sub": "alice",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "scope": "animations:write",
    }
    token = jwt.encode(claims, key, algorithm="RS256")
    assert await auth.identity("Bearer " + token)
    for change in [
        {"aud": "https://wrong.example"},
        {"exp": 0},
        {"scope": "read"},
        {"iss": "https://wrong.example"},
    ]:
        with pytest.raises(ValueError):
            await auth.identity(
                "Bearer " + jwt.encode(claims | change, key, algorithm="RS256")
            )


def test_tunnel_loopback_host_remains_authenticated(service):
    with TestClient(create_app(service), base_url="http://127.0.0.1:8787") as c:
        assert c.post("/mcp").status_code == 401
        result = rpc(
            c,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "tunnel", "version": "1"},
            },
        )
        assert result["result"]["serverInfo"]["name"] == "Manim Animation"
        blocked = c.post(
            "/mcp",
            headers={"Host": "attacker.example", "Authorization": "Bearer " + "x" * 40},
            json={"jsonrpc": "2.0", "id": 4, "method": "tools/list"},
        )
        assert blocked.status_code == 421


def test_oauth_metadata_is_advertised_when_configured(service):
    service.auth = Auth(
        "http://testserver",
        issuer="https://identity.example",
        audience="manim",
        jwks_url="https://identity.example/jwks",
    )
    with TestClient(create_app(service)) as c:
        assert "resource_metadata" in c.post("/mcp").headers["www-authenticate"]
        response = c.get("/.well-known/oauth-protected-resource")
        assert response.status_code == 200
        assert response.json()["authorization_servers"] == ["https://identity.example"]
