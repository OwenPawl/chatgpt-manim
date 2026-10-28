"""Reproducible mathematical example specifications; no model or API dependency."""

import json, math
from pathlib import Path


def save(name, title, description, objects, steps):
    Path("examples/" + name + ".json").write_text(
        json.dumps(
            dict(
                title=title,
                description=description,
                resolution="720p",
                fps=30,
                objects=objects,
                steps=steps,
            ),
            indent=2,
        )
        + "\n"
    )


def text(id, s, x, y, size=28, color="#E5EDF8"):
    return dict(
        id=id, kind="text", text=s, position=[x, y], font_size=size, color=color
    )


def step(action, target=None, duration=1, **kw):
    return dict(action=action, target=target, duration=duration, **kw)


objects = [
    text("title", "A signal, seen two ways", 0, 3, 36),
    text("time", "TIME DOMAIN", -3, 2, 20, "#70D6FF"),
    text("freq", "FREQUENCY DOMAIN", 3, 2, 20, "#FFD166"),
    dict(
        id="formula",
        kind="math",
        text=r"f(t)=\sin(t)+0.5\sin(3t)",
        position=[0, -2.8],
        font_size=32,
        color="#E5EDF8",
    ),
]
for id, f, color in [
    ("fundamental", lambda t: math.sin(t), "#70D6FF"),
    ("harmonic", lambda t: 0.5 * math.sin(3 * t), "#EF8CB5"),
    ("signal", lambda t: math.sin(t) + 0.5 * math.sin(3 * t), "#FFD166"),
]:
    points = [[-5.8 + 5.4 * i / 160, f(2 * math.pi * i / 160)] for i in range(161)]
    objects.append(dict(id=id, kind="polyline", points=points, color=color))
objects.extend(
    [
        dict(
            id="axis", kind="line", points=[[0.9, -1.4], [5.8, -1.4]], color="#64748B"
        ),
        dict(
            id="bar1",
            kind="rectangle",
            width=0.5,
            height=2,
            position=[2, -0.4],
            fill_opacity=0.8,
            color="#70D6FF",
        ),
        dict(
            id="bar3",
            kind="rectangle",
            width=0.5,
            height=1,
            position=[4, -0.9],
            fill_opacity=0.8,
            color="#EF8CB5",
        ),
        text("label1", "1 Hz", 2, -1.8, 22),
        text("label3", "3 Hz", 4, -1.8, 22),
        text("caption", "Each peak records a sine component’s amplitude.", 0, -2.2, 22),
    ]
)
s = [
    step("write", "title"),
    step("write", "time", 0.5),
    step("write", "formula"),
    step("create", "fundamental", 1.5),
    step("create", "harmonic", 1.5),
    step("create", "signal", 2),
    step("fade_out", "fundamental", 0.4),
    step("fade_out", "harmonic", 0.4),
    step("write", "freq", 0.5),
    step("create", "axis", 0.5),
    step("create", "bar1"),
    step("write", "label1", 0.3),
    step("create", "bar3"),
    step("write", "label3", 0.3),
    step("write", "caption"),
    step("wait", duration=2),
]
save(
    "fourier",
    "Fourier: from waves to components",
    "A finite sine-series example: amplitudes 1 at 1 Hz and 0.5 at 3 Hz. Peaks use an amplitude-spectrum convention; phases and negative frequencies are omitted.",
    objects,
    s,
)
objects = [
    text("title", "A collision does not lose a key", 0, 3, 36),
    text("hash", "h(key) = key mod 4", 0, 2.25, 28),
    text("caption", "Separate chaining keeps both keys in bucket 1.", 0, -2.5, 26),
]
for i in range(4):
    objects.extend(
        [
            dict(
                id=f"b{i}",
                kind="rectangle",
                width=1.1,
                height=0.8,
                position=[-4, 1.25 - i],
                color="#64748B",
            ),
            text(f"l{i}", str(i), -4, 1.25 - i, 24),
        ]
    )
objects.extend(
    [
        dict(
            id="n5",
            kind="rectangle",
            width=1.2,
            height=0.8,
            position=[-0.8, 0.25],
            color="#70D6FF",
            fill_opacity=0.15,
        ),
        text("k5", "5", -0.8, 0.25),
        dict(
            id="n9",
            kind="rectangle",
            width=1.2,
            height=0.8,
            position=[2, 0.25],
            color="#FFD166",
            fill_opacity=0.15,
        ),
        text("k9", "9", 2, 0.25),
        dict(
            id="a1", kind="arrow", points=[[-3.4, 0.25], [-1.5, 0.25]], color="#70D6FF"
        ),
        dict(
            id="a2", kind="arrow", points=[[-0.15, 0.25], [1.3, 0.25]], color="#FFD166"
        ),
        text("null", "null", 4.5, 0.25, 24),
        dict(
            id="a3", kind="arrow", points=[[2.65, 0.25], [3.8, 0.25]], color="#64748B"
        ),
    ]
)
s = [step("write", "title"), step("write", "hash")]
for i in range(4):
    s.extend([step("create", f"b{i}", 0.2), step("write", f"l{i}", 0.2)])
s.extend(
    [
        step("indicate", "b1"),
        step("create", "a1", 0.5),
        step("create", "n5", 0.5),
        step("write", "k5", 0.5),
        step("wait"),
        step("indicate", "b1", color="#FFD166"),
        step("create", "a2", 0.5),
        step("create", "n9", 0.5),
        step("write", "k9", 0.5),
        step("create", "a3", 0.5),
        step("write", "null", 0.4),
        step("write", "caption"),
        step("wait", duration=2),
    ]
)
save(
    "hash-chaining",
    "Hash collisions · separate chaining",
    "5 mod 4 = 9 mod 4 = 1. The second key joins the linked list at bucket 1; a collision does not overwrite the first key.",
    objects,
    s,
)
objects = [
    text("title", "Rotation preserves shape and distance", 0, 3, 34),
    dict(
        id="shape",
        kind="polygon",
        points=[[-1, -1], [1, -1], [0, 1]],
        color="#70D6FF",
        fill_opacity=0.25,
    ),
    dict(
        id="formula",
        kind="math",
        text=r"R(\theta)=\begin{pmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{pmatrix}",
        position=[0, -2.3],
        font_size=30,
        color="#E5EDF8",
    ),
    text("caption", "90° rotation, then a translation", 0, 2.15, 26),
]
s = [
    step("write", "title"),
    step("create", "shape"),
    step("write", "formula", 1.5),
    step("write", "caption"),
    step("rotate", "shape", 2, angle=math.pi / 2),
    step("wait"),
    step("move", "shape", 2, position=[2, 0]),
    step("color", "shape", 1, color="#FFD166"),
    step("wait", duration=2),
]
save(
    "geometry",
    "Geometry · rotation and translation",
    "Watch a triangle rotate 90 degrees about its center, then translate two units to the right. Both transformations preserve lengths and angles.",
    objects,
    s,
)
