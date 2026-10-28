# Contributing

Use Python 3.12 or newer and rootless Podman on Linux. Follow the README setup,
run `pytest -q`, then build the worker and run `MANIM_INTEGRATION=1 pytest -q`.
Keep generated scene input declarative: do not introduce eval, exec, arbitrary
TeX, user-selected files, network requests, or source-code execution. Extend the
schema, trusted renderer and failure cases together.

For player changes, verify a real MP4 in the MCP Apps test host, including
play/pause, scrubbing, speed, dark/light mode and narrow widths. Report whether
verification used a simulated host or actual ChatGPT; they are different tests.
For model-selection changes, replay `tests/prompts.json` in an installed plugin
and record observed tool calls. Fixture validation is not model evaluation.

Open a focused pull request describing the behavior, rationale, and checks.
Never commit credentials, `.env`, private scenes or generated job data.
