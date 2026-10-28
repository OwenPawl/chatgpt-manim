# Deployment

## Recommended small-host architecture

Use an existing Linux host or VM with rootless Podman and cgroups v2. Run the
MCP service as a dedicated unprivileged OS user. Build the worker there, install
the Python service, store its secrets in an owner-readable environment file,
and supervise `scripts/serve.py` with systemd. Put an HTTPS reverse proxy in front
of loopback port 8787. Only proxy `/mcp`, `/media/*`, `/healthz` and the protected
resource metadata endpoint. Do not expose preview routes in production.

A container-capable hosting plan must permit the required isolation/runtime
features. Generic serverless functions and ordinary unprivileged PaaS containers
cannot be assumed to support nested container launch. Do not silently fall back
to executing scenes in the server process.

```sh
podman build -f worker/Dockerfile -t localhost/chatgpt-manim-worker:0.1.0 .
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps .
```

Set `MANIM_BASE_URL=https://your-domain`, `MANIM_SIGNING_KEY` to a random secret,
and these OAuth settings:

- `MANIM_OAUTH_ISSUER`: exact HTTPS issuer, including its trailing slash if applicable.
- `MANIM_OAUTH_AUDIENCE`: the registered resource, normally `https://your-domain/mcp`.
- `MANIM_OAUTH_JWKS_URL`: fixed HTTPS JWKS URL controlled by your identity provider.

Register the `animations:write` scope with the provider. Configure OAuth 2.1
PKCE S256, resource indicators, authorization-server metadata, and a ChatGPT
client via supported CIMD, dynamic registration or provided-client settings.
Use an established provider; this repository deliberately does not implement a
password database or custom authorization server. Unset `MANIM_API_KEY` in an
OAuth-only production deployment. Missing authentication configuration stops startup.

The reverse proxy should preserve Host, stream MP4 range responses, limit request
bodies to 256 KiB, apply an unauthenticated/IP rate limit before token verification,
and avoid logging authorization headers or media query strings. Apply host firewall,
patching, disk quotas and private backups. Monitor failed jobs, queue saturation,
storage growth and `/healthz`. Restarted in-progress renders become failed and can
be retried; no claim of exactly-once execution is made.

## Containerizing the server

`Dockerfile` builds the MCP controller independently of the Manim worker. The
included `compose.yaml` talks to a **rootless user Podman socket**. Enable it with
`systemctl --user enable --now podman.socket`; prepare `data/` for the mapped UID,
set `.env`, then use your Compose implementation. Set `MANIM_WORKER_IMAGE` to the
image already built on that runtime. The controller receives container-launch
authority for that OS account, so dedicate the account to this service. Never
substitute a root Docker socket. Workers themselves never receive this socket.
SELinux hosts may need a narrowly scoped socket policy; do not disable SELinux
host-wide. The native-controller path was verified on Fedora; Compose runtime
integration remains an operator validation step.

## Free development HTTPS

A Cloudflare Quick Tunnel can expose the authenticated local service without an
account or cloud bill:

```sh
cloudflared tunnel --url http://127.0.0.1:8787 --no-autoupdate
```

Set `MANIM_BASE_URL` to the printed HTTPS origin and restart the service. Run
`scripts/smoke_remote.py` to verify initialization, an authenticated real render,
and range streaming. Keep the bearer protection enabled. Quick Tunnels have no
uptime guarantee, change hostname on restart, and do not support SSE; this server
uses stateless JSON HTTP responses and async status polling. They are testing
infrastructure, not production hosting or a public-submission endpoint.

A temporary development tunnel was verified during implementation. It depends on
the developer machine, service and tunnel process remaining online. The current
URL belongs in the local status file, not a permanent installation manifest.

## Costs and approvals

Local execution uses existing hardware, disk and electricity, with no LLM API
charges. No paid service was provisioned for this project. A dedicated VM, stable
domain, object storage or managed IdP may incur charges; select and approve a
specific plan before provisioning. No fixed provider price is promised here.
Budget for roughly 2 GiB per active render plus controller overhead and retained
media; defaults permit at most 100 × 32 MiB of output, excluding database/backups.

References: [OpenAI MCP hosting requirements](https://developers.openai.com/plugins/build/mcp-server),
[OAuth requirements](https://developers.openai.com/plugins/build/auth),
[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

The application also applies a bounded global 600-request/minute MCP ingress
limit before credential verification, and 120 requests/minute per authenticated
owner. This is single-process protection, not a distributed DDoS defense.
Stateless `/mcp` accepts POST; optional long-lived GET/SSE streams are disabled.
