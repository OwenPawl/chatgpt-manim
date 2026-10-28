---
name: manim-animation
description: Render and revise mathematical or computational animations with Manim when the user asks for animation or a dynamic visual explanation. Prefer text and static diagrams when motion adds no value.
---

Use the connected Manim tools when an animation is the requested output, including algorithm steps, geometric transformations, changing graphs, and mathematical processes. Do not invoke for unrelated work, static plots, definitions, or requests that explicitly exclude animation. Tool selection is advisory; this is a plugin, not a native ChatGPT output renderer.

1. Decide what change over time clarifies the idea. Keep the explanation mathematically accurate; animations supplement necessary reasoning.
2. Call `animation_capabilities` if the scene vocabulary is unfamiliar. Author the complete declarative scene yourself; there is no second model API. Never submit Python, SVG, URLs, or arbitrary LaTeX commands.
3. Give each object a stable ID and explicitly create or write it before manipulating it. Coordinates use a roughly 14.2 × 8 scene, centered at the origin. Timeline steps are sequential. A polyline uses sampled points; calculate those points rather than sending an expression to evaluate. Math supports the documented safe notation allowlist.
4. Call `render_animation`. Keep the returned animation ID in the conversation. Call `get_animation` until ready or failed, allowing a few seconds between polls; do not submit duplicate renders while waiting. The widget also polls. Explain actual errors and revise only the relevant scene details.
5. For follow-ups, retrieve the original specification with `get_animation`. Preserve its decisions and call `revise_animation` with its ID, the user's instructions, and the full updated spec. For “twice as slow,” multiply the previous `pacing` value by two (subject to the 90-second total limit). Playback-only speed changes can use the player's speed control without rendering again.
6. The ready result displays the embedded player on supporting MCP Apps hosts. Refer to that result rather than telling the user to run Python or download a file. Never claim rendering, installation, automatic invocation, or ChatGPT display succeeded without observed evidence.

Supported objects: text, math, circle, rectangle, line, arrow, polygon, axes, polyline. Supported steps: create, write, fade_in, fade_out, move, rotate, scale, color, transform, wait, indicate. Use replacements for transform; rotation is in radians around the object's center. See [examples](../../examples) for complete scenes.
