from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, urlencode
import hashlib
import hmac
import json
import os
import re
import time
from typing import Literal
from pydantic import BaseModel
from mcp.server.mcpserver import MCPServer, Context
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations, CallToolResult, TextContent
from starlette.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.routing import Route
from .scene import SceneSpec, TEX_COMMANDS
from .renderer import ContainerRenderer
from .store import Store
from .auth import Auth, Guard

ROOT = Path(__file__).resolve().parents[2]
UI_URI = "ui://manim/player-v1.html"


class AnimationResult(BaseModel):
    """Schema for model-visible structuredContent, separate from the MCP envelope."""

    id: str
    status: Literal["queued", "rendering", "ready", "failed"]
    error: str | None
    parent: str | None
    instructions: str
    created: float
    spec: SceneSpec
    cached: bool


class Service:
    def __init__(self, store, auth, signing_key, ui_path=None, preview=False):
        if len(signing_key) < 32:
            raise ValueError("Media signing key must be at least 32 characters")
        self.store = store
        self.auth = auth
        self.key = signing_key.encode()
        self.ui_path = ui_path or Path(
            os.getenv("MANIM_UI_PATH", str(Path(__file__).parent / "ui/player.html"))
        )
        self.preview = preview

    def signature(self, job_id, expires, purpose):
        return hmac.new(
            self.key, f"{purpose}:{job_id}:{expires}".encode(), hashlib.sha256
        ).hexdigest()

    def url(self, job_id, purpose="media"):
        expires = int(time.time()) + 900
        return f"{self.auth.base_url}/{purpose}/{job_id}?" + urlencode(
            {"expires": expires, "signature": self.signature(job_id, expires, purpose)}
        )

    def check(self, request, purpose):
        job_id = request.path_params["job_id"]
        if not re.fullmatch("[0-9a-f]{32}", job_id):
            raise ValueError("Invalid animation ID")
        try:
            expires = int(request.query_params.get("expires", "0"))
        except ValueError:
            raise ValueError("Invalid expiry")
        signature = request.query_params.get("signature", "")
        if (
            expires < time.time()
            or expires > time.time() + 901
            or not hmac.compare_digest(
                signature, self.signature(job_id, expires, purpose)
            )
        ):
            raise ValueError("Media link expired or invalid; refresh animation status")
        return job_id

    def result(self, row, cached=False):
        data = {
            k: row[k]
            for k in ("id", "status", "error", "parent", "instructions", "created")
        }
        data.update({"spec": json.loads(row["spec"]), "cached": cached})
        # Signed media is only delivered to the widget, not placed in model-visible text.
        meta = {"media_url": self.url(row["id"])} if row["status"] == "ready" else {}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(data))],
            structuredContent=data,
            _meta=meta,
        )

    async def media(self, request):
        try:
            job_id = self.check(request, "media")
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=403)
        if len(request.headers.get("range", "")) > 256:
            return JSONResponse({"error": "Range header too large"}, status_code=416)
        file = self.store.path / (job_id + ".mp4")
        if not file.is_file():
            return JSONResponse({"error": "Animation not available"}, status_code=404)
        return FileResponse(
            file,
            media_type="video/mp4",
            filename="animation.mp4",
            content_disposition_type="inline",
            headers={
                "Cache-Control": "private, no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    async def preview_page(self, request):
        try:
            job_id = self.check(request, "preview")
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=403)
        row = self.store.db.execute(
            "SELECT * FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        if not row:
            return JSONResponse({"error": "Not found"}, status_code=404)
        result = self.result(dict(row)).model_dump(by_alias=True)
        payload = json.dumps(result).replace("<", "\\u003c")
        # Local test host implements the documented bridge; it is not ChatGPT verification.
        return HTMLResponse(
            '<!doctype html><title>Manim MCP Apps test host</title><style>body{margin:32px auto;max-width:900px;background:#eef1f5;font-family:system-ui}iframe{width:100%;height:760px;border:0;border-radius:20px}</style><h1>Manim · MCP Apps test host</h1><iframe id="app" allow="fullscreen" sandbox="allow-scripts allow-same-origin allow-downloads"></iframe><script>const result='
            + payload
            + ';const frame=document.getElementById("app");frame.srcdoc='
            + json.dumps(self.ui_path.read_text()).replace("<", "\\u003c")
            + ';addEventListener("message",e=>{if(e.source!==frame.contentWindow)return;let m=e.data;if(m.method==="ui/initialize")frame.contentWindow.postMessage({jsonrpc:"2.0",id:m.id,result:{protocolVersion:"2026-01-26",hostInfo:{name:"local-test",version:"1"},hostCapabilities:{},hostContext:{theme:"light"}}},"*");if(m.method==="ui/notifications/initialized")frame.contentWindow.postMessage({jsonrpc:"2.0",method:"ui/notifications/tool-result",params:result},"*");if(m.method==="tools/call")frame.contentWindow.postMessage({jsonrpc:"2.0",id:m.id,result},"*");});</script>',
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )


def create_app(service):
    mcp = MCPServer(
        "Manim Animation",
        version="0.1.0",
        instructions="Use animations for explicit animation requests or dynamic mathematical/computational explanations. Prefer text or static visuals when sufficient. Author a bounded SceneSpec, never Python. Retrieve prior spec before revising. No second LLM is called. Render asynchronously, then poll status until ready or failed; do not claim success while queued.",
    )
    scheme = (
        [{"type": "oauth2", "scopes": ["animations:write"]}]
        if service.auth.issuer
        else []
    )
    ui_meta = {"ui": {"resourceUri": UI_URI}, "openai/outputTemplate": UI_URI}
    if scheme:
        ui_meta["securitySchemes"] = scheme
    readonly = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=False,
        idempotentHint=True,
    )
    write = ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=False,
        idempotentHint=True,
    )

    # MCP SDK validates envelope.structuredContent against each annotated output model.
    # Returning CallToolResult preserves widget-only _meta and error envelopes.
    def owner(ctx):
        return ctx.request_context.request.state.owner

    @mcp.tool(annotations=write, meta=ui_meta)
    async def render_animation(spec: SceneSpec, ctx: Context) -> AnimationResult:
        """Use when the user asks to animate a mathematical or computational concept. Submit a complete declarative scene and return a job ID; poll get_animation. Do not use for unrelated requests or static explanations that suffice."""
        try:
            row, cached = service.store.submit(owner(ctx), spec)
            return service.result(row, cached)
        except ValueError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=str(e))], isError=True
            )

    @mcp.tool(annotations=readonly, meta=ui_meta)
    async def get_animation(animation_id: str, ctx: Context) -> AnimationResult:
        """Get render status, errors, full original scene specification and a refreshed playable result. Use before revising an existing animation and to poll pending jobs."""
        try:
            return service.result(service.store.get(owner(ctx), animation_id))
        except ValueError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=str(e))], isError=True
            )

    @mcp.tool(annotations=write, meta=ui_meta)
    async def revise_animation(
        animation_id: str,
        instructions: str,
        ctx: Context,
        spec: SceneSpec | None = None,
        pacing: float | None = None,
    ) -> AnimationResult:
        """Revise an existing scene preserving lineage. For slowdown supply pacing (absolute duration multiplier); otherwise the model must supply the complete updated spec. Instructions record the user's intent; the server does not interpret natural language. Original animation is retained."""
        try:
            old = service.store.get(owner(ctx), animation_id)
            if len(instructions) > 1200:
                raise ValueError("Instructions exceed 1200 characters")
            if spec is None and pacing is None:
                raise ValueError("Provide a revised spec or pacing value")
            data = spec.model_dump() if spec else json.loads(old["spec"])
            if pacing is not None:
                data["pacing"] = pacing
            updated = SceneSpec.model_validate(data)
            row, cached = service.store.submit(
                owner(ctx), updated, animation_id, instructions
            )
            return service.result(row, cached)
        except ValueError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=str(e))], isError=True
            )

    @mcp.tool(annotations=readonly, meta={"securitySchemes": scheme} if scheme else {})
    async def animation_capabilities() -> dict:
        """Get supported shapes, notation, timing limits, safe scene schema and MP4 output capabilities before constructing an unfamiliar scene."""
        return {
            "engine": "Manim Community 0.22.1",
            "format": "MP4 H.264 yuv420p",
            "source": "declarative JSON only",
            "max_duration_seconds": 90,
            "supported_math_commands": sorted(TEX_COMMANDS),
            "resolutions": ["480p", "720p", "1080p"],
            "schema": SceneSpec.model_json_schema(),
        }

    @mcp.resource(
        UI_URI,
        mime_type="text/html;profile=mcp-app",
        meta={
            "ui": {
                "prefersBorder": True,
                "domain": service.auth.base_url,
                "csp": {
                    "resourceDomains": [service.auth.base_url],
                    "connectDomains": [],
                },
                "permissions": {"fullscreen": {}},
            }
        },
    )
    def player() -> str:
        return service.ui_path.read_text()

    hostname = urlparse(service.auth.base_url).netloc
    app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        max_request_body_size=262144,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[hostname],
            allowed_origins=[service.auth.base_url],
        ),
    )
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with original(app):
            try:
                yield
            finally:
                await service.store.close()

    app.router.lifespan_context = lifespan

    async def health(request):
        return JSONResponse({"status": "ok", "version": "0.1.0"})

    async def metadata(request):
        return JSONResponse(service.auth.metadata())

    app.router.routes.extend(
        [
            Route("/healthz", health),
            Route("/media/{job_id}", service.media, methods=["GET", "HEAD"]),
            Route("/.well-known/oauth-protected-resource", metadata),
        ]
    )
    if service.preview:
        app.router.routes.append(Route("/preview/{job_id}", service.preview_page))
    app.add_middleware(Guard, auth=service.auth)
    app.state.service = service
    app.state.mcp = mcp
    return app


def from_env():
    base = os.getenv("MANIM_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
    if urlparse(base).scheme != "https" and urlparse(base).hostname not in (
        "127.0.0.1",
        "localhost",
    ):
        raise ValueError("Remote deployment requires HTTPS")
    auth = Auth(
        base,
        os.getenv("MANIM_API_KEY", ""),
        os.getenv("MANIM_OAUTH_ISSUER", ""),
        os.getenv("MANIM_OAUTH_AUDIENCE", ""),
        os.getenv("MANIM_OAUTH_JWKS_URL", ""),
    )
    renderer = ContainerRenderer(
        os.getenv("MANIM_RUNTIME", "podman"),
        os.getenv("MANIM_WORKER_IMAGE", "localhost/chatgpt-manim-worker:0.1.0"),
        int(os.getenv("MANIM_RENDER_TIMEOUT", "180")),
    )
    store = Store(Path(os.getenv("MANIM_DATA_DIR", "data")), renderer)
    return create_app(
        Service(
            store,
            auth,
            os.environ["MANIM_SIGNING_KEY"],
            preview=os.getenv("MANIM_ENABLE_PREVIEW") == "1",
        )
    )


def main():
    import uvicorn

    uvicorn.run(
        from_env(),
        host=os.getenv("MANIM_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8787")),
        access_log=False,
    )


if __name__ == "__main__":
    main()
