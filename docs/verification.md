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

## Actual ChatGPT Work verification

On 2026-10-27, the private Secure MCP Tunnel and personal plugin were provisioned
and connected in the account. The following were observed in Chrome, using
ChatGPT Work's GPT-6.1 Sol Light setting:

- Explicitly selected request: blue circle → green square, 720p, 5.5 seconds.
- Follow-up: twice as slow and orange square, 11 seconds, same title and parent
  animation ID, with `pacing=2` and the changed replacement color in storage.
- Untagged request: “Animate a blue triangle rotating 90 degrees, then moving to
  the right. Keep it short and display the playable animation here.” The model
  selected Manim automatically and produced a real 3-second MP4.
- Negative follow-up: “In one sentence, what is 2 + 2? Do not create an animation
  or use any tools.” Answered “2 + 2 equals 4.” with no new animation/tool call.
- Actual HTML5 playback was observed in both the inline response card and
  ChatGPT's side panel. Playback speed selected 1.5×. The revision played through
  to the orange final frame at 0:11 / 0:11. Screenshots are
  `assets/chatgpt-inline.png` and `assets/chatgpt-revision.png`.

**Host limitations:** each tested initial app load failed; the host's **Try again**
button then loaded the player. This is a repeatable workaround, not a verified
permanent fix. Fullscreen was rejected by the host and the player displayed its
fallback error. The account's pre-existing “Enforce CSP for custom apps” switch
was off; it was left unchanged. The server returns standard CSP metadata, but
strict enforcement in ChatGPT has not been verified.

The bundled skill is present in the portable repository package. The installed
cloud plugin is the MCP connection with its tool descriptions; it does not yet
include the repository skill. The untagged invocation above tests discovery of
that installed connection. A single positive and negative case is evidence of
those runs, not a general guarantee of correct model selection.

A separate standard **Chat** conversation explicitly requested the installed Manim
plugin. It rendered a moving blue circle and played inline after the same host
retry. Standard Chat showed a “This response couldn’t load” message for the text
response, although the tool result and player worked. Untagged selection and
follow-up revision in standard Chat were not tested. These results apply to this
account and tested UI; availability can differ across accounts.

## Not yet verified or complete

- A stable production deployment and external OAuth provider integration.
- Public plugin directory submission/approval.
- Multi-replica operation (explicitly unsupported), production load/abuse testing,
  or an independent security audit.
- Docker Compose runtime socket integration; the native controller with rootless
  Podman workers is the verified runtime configuration.

`tests/prompts.json` contains additional labeled cases. Its fixture/schema test
checks the dataset; it does **not** prove model selection for every prompt.

| Environment | Positive selection | Negative avoidance | Follow-up revision | Embedded display |
| --- | --- | --- | --- | --- |
| ChatGPT Work | Explicit and untagged passed | One explicit no-animation case passed | Pacing + color passed | Inline + side panel, after host retry |
| Standard Chat | Explicitly named plugin passed | Not run | Not run | Inline playback after host retry |
| MCP client + bridge test host | Direct tool call passed | Not a model test | Service test passed | Passed |

The current fast suite has 31 passing tests, including new regression checks for
private loopback MCP authentication, rejected foreign Host headers, bearer-only
OAuth discovery behavior, and unchanged OAuth resource metadata. Three separate
real-worker integration checks passed in the initial run and run again in CI.

Both worker and server container images built successfully. A network-disabled
server-image check confirmed that the installed Python package includes its UI
resource (the wheel does not depend on a source checkout).

A second HTTPS smoke run revised the Fourier scene to twice its original pacing,
rendered it to completion, verified its 29.8-second MP4 duration, and repeated the
same revision to confirm cache reuse without another render. Tool discovery also
advertises a validated structured output schema for animation results.
