# Verification record

Verified on 2026-10-27 (America/Los_Angeles), Fedora Linux, Python 3.14,
rootless Podman 5.8.4, Manim CE 0.22.1 and official MCP Python SDK 2.3.0.

## Automated checks

- MCP Streamable HTTP initialization and four-tool discovery.
- MCP Apps resource retrieval, MIME, UI linkage and CSP metadata.
- Valid example specs; invalid types, bounds, unknown targets, timeline limits,
  arbitrary Python fields and TeX file/macro/encoded-escape attempts rejected.
- Auth failure, OAuth signature/issuer/audience/expiry/scope checks, origin checks,
  per-owner request limits and quotas.
- Render submission, status, errors, revisions and preserved parent specification.
- Owner-scoped cache and inaccessible foreign jobs, restart recovery state.
- Expired/tampered media signatures and successful HTTP 206 byte ranges.
- Real Manim mathematical notation rendered to H.264/yuv420p MP4.
- Real container UID, absent credentials, blocked outbound network, read-only root,
  zero effective capabilities, 2 GiB memory, 128 PIDs and 2 CPU limits.
- Real render timeout and explicit container cleanup.
- Portable manifests validated against downloaded official Agent Plugins schemas;
  skill validated with the official skill-creator validator.

Run `pytest -q` for fast checks; opt into the three container tests with
`MANIM_INTEGRATION=1 pytest -q tests/test_integration.py`.

## End-to-end service and browser

All three example MP4s were rendered in the isolated worker. An authenticated
request through a temporary HTTPS Cloudflare tunnel initialized MCP, rendered
the Fourier scene, polled it to ready and retrieved a byte range from its signed
media URL. Anonymous MCP requests returned 401.

The real player loaded in a sandboxed iframe using an implementation of the
standard MCP Apps bridge. Chrome decoded 1280×720 frames, advanced playback time,
paused, changed speed to 1.5× and scrubbed to the 14.9-second end. The screenshot
in `assets/player-screenshot.png` is from that test. Fullscreen was denied by the
host and the component displayed its fallback error; fullscreen availability
must be rechecked in the target host.

## Not yet verified

- Actual ChatGPT installation, UI rendering, positive/negative automatic model
  selection and follow-up invocations. The signed-in ChatGPT custom-server dialog
  was inspected, but it cannot use the development fixed bearer credential.
- A stable production deployment and external OAuth provider integration.
- The private Secure MCP Tunnel path: Platform tunnel settings required login.
- Multi-replica operation (explicitly unsupported), production load/abuse testing,
  or an independent security audit.
- Docker Compose runtime socket integration; the native controller with rootless
  Podman workers is the verified runtime configuration.

`tests/prompts.json` contains labeled evaluation cases. Its fixture/schema test
only checks the dataset; it does **not** prove that a model selects or avoids a
tool. Record actual ChatGPT runs in the table below after installation.

| Environment | Positive selection | Negative avoidance | Follow-up revision | Embedded display |
| --- | --- | --- | --- | --- |
| ChatGPT Work | Not run | Not run | Not run | Not run |
| Standard Chat | Not run | Not run | Not run | Not run |
| MCP client + bridge test host | Direct tool call passed | Not a model test | Service test passed | Passed |

Both worker and server container images built successfully. A network-disabled
server-image check confirmed that the installed Python package includes its UI
resource (the wheel does not depend on a source checkout).

A second HTTPS smoke run revised the Fourier scene to twice its original pacing,
rendered it to completion, verified its 29.8-second MP4 duration, and repeated the
same revision to confirm cache reuse without another render. Tool discovery also
advertises a validated structured output schema for animation results.
