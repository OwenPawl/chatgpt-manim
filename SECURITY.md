# Security

This is a bounded declarative renderer, not a Python execution service. Workers
run disposable OCI containers with no network, no mounts, a read-only root,
non-root UID, dropped capabilities, no-new-privileges, seccomp, bounded tmpfs,
2 CPU / 2 GiB / 128 PID limits and a 180-second deadline. The server explicitly
removes timed-out containers. No credentials are passed to workers.

LaTeX is restricted to a small notation allowlist and rendered inside the same
boundary. The schema limits text, points, objects, timeline steps, resolution,
frame rate and total duration. Output is H.264 MP4, capped at 32 MiB. No Python,
external fonts, SVG uploads, expression evaluation or arbitrary files are accepted.

OCI containers share the host kernel. This is defense in depth for a restricted
scene language, not a claim that containers alone safely sandbox arbitrary Python.
For arbitrary source support, use a separately audited microVM/sandbox design.

The HTTP service fails closed unless authentication is configured. OAuth tokens
are checked against configured JWKS, algorithm allowlist, issuer, audience,
expiry and scope. Fixed bearer mode is for personal/development clients; it does
not implement OAuth. Media links grant access to one MP4 for 15 minutes, so treat
them as credentials. Logs omit access URLs and bearer secrets. Cache entries and
scene queries are owner-scoped. See deployment documentation for reverse-proxy
limits, rootless runtime socket permissions and identity-provider setup.

Do not open public issues containing exploitable details or secrets. Use the
repository's private vulnerability reporting feature when enabled; otherwise
contact the maintainer privately via their GitHub profile before disclosing.
