"""Bounded declarative vocabulary. Never eval Python, expressions, SVG, or TeX input."""

from typing import Literal, Annotated
import re
from pydantic import BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(ge=-100, le=100, allow_inf_nan=False)]
Point = tuple[Number, Number]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$")]
# This grammar is intentionally small: LaTeX file I/O, macros and packages are not a feature.
TEX_COMMANDS = set(
    "frac sqrt sin cos tan log ln exp sum prod int pi theta alpha beta gamma delta omega sigma phi lambda mu infinity infty cdot times pm le ge neq approx to rightarrow leftarrow vec hat bar overline underline left right begin end matrix pmatrix bmatrix cases text mathrm mathbf mathbb quad qquad limits partial nabla".split()
)


def safe_math(value: str) -> str:
    if (
        "^^" in value
        or len(value) > 500
        or re.search(r"[^a-zA-Z0-9\\{}_^+\-=()., /|\[\]:;&<>!\n]", value)
    ):
        raise ValueError("Math contains unsupported characters")
    commands = re.findall(r"\\([a-zA-Z]+|.)", value)
    if any(
        c not in TEX_COMMANDS and c not in ("\\", ",", ";", "!", " ") for c in commands
    ):
        raise ValueError("Math command is outside the safe notation allowlist")
    for env in re.findall(r"\\(?:begin|end)\{([^}]+)\}", value):
        if env not in {"matrix", "pmatrix", "bmatrix", "cases"}:
            raise ValueError("Unsupported math environment")
    if value.count("{") != value.count("}"):
        raise ValueError("Unbalanced math braces")
    return value


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Item(Strict):
    id: Identifier
    kind: Literal[
        "text",
        "math",
        "circle",
        "rectangle",
        "line",
        "arrow",
        "polygon",
        "axes",
        "polyline",
    ]
    text: str = Field(default="", max_length=500)
    position: Point = (0, 0)
    color: Color = "#70D6FF"
    width: float = Field(default=1, gt=0, le=12)
    height: float = Field(default=1, gt=0, le=7)
    radius: float = Field(default=0.4, gt=0, le=4)
    font_size: int = Field(default=32, ge=12, le=96)
    points: list[Point] = Field(default_factory=list, max_length=1000)
    fill_opacity: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def check(self):
        if self.kind == "math":
            safe_math(self.text)
        minimum = {"line": 2, "arrow": 2, "polygon": 3, "polyline": 2}.get(self.kind, 0)
        if len(self.points) < minimum:
            raise ValueError(f"{self.kind} needs {minimum} points")
        if self.kind in ("line", "arrow") and self.points[0] == self.points[1]:
            raise ValueError("Line endpoints must differ")
        return self


class Step(Strict):
    action: Literal[
        "create",
        "write",
        "fade_in",
        "fade_out",
        "move",
        "rotate",
        "scale",
        "color",
        "transform",
        "wait",
        "indicate",
    ]
    target: Identifier | None = None
    duration: float = Field(default=1, ge=0.1, le=15)
    position: Point | None = None
    angle: float = Field(default=0, ge=-12.57, le=12.57)
    factor: float = Field(default=1, ge=0.1, le=5)
    color: Color | None = None
    replacement: Item | None = None


class SceneSpec(Strict):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1200)
    resolution: Literal["480p", "720p", "1080p"] = "720p"
    fps: Literal[15, 24, 30] = 30
    background: Color = "#101827"
    pacing: float = Field(
        default=1,
        ge=0.25,
        le=4,
        description="Multiply every step duration; 2 makes the scene twice as slow.",
    )
    objects: list[Item] = Field(min_length=1, max_length=100)
    steps: list[Step] = Field(min_length=1, max_length=150)

    @model_validator(mode="after")
    def validate_timeline(self):
        ids = [x.id for x in self.objects]
        if len(set(ids)) != len(ids):
            raise ValueError("Object IDs must be unique")
        visible = set()
        for s in self.steps:
            if s.action == "wait":
                continue
            if s.target not in ids:
                raise ValueError(f"Unknown target: {s.target}")
            if s.action in ("create", "write", "fade_in"):
                if s.target in visible:
                    raise ValueError("Object is already visible")
                visible.add(s.target)
            else:
                if s.target not in visible:
                    raise ValueError(f"Target {s.target} must first appear")
                if s.action == "fade_out":
                    visible.remove(s.target)
            if s.action == "move" and s.position is None:
                raise ValueError("move requires position")
            if s.action == "color" and s.color is None:
                raise ValueError("color requires color")
            if s.action == "transform" and s.replacement is None:
                raise ValueError("transform requires replacement")
        if sum(s.duration for s in self.steps) * self.pacing > 90:
            raise ValueError("Maximum total duration is 90 seconds")
        if sum(len(o.points) for o in self.objects) > 5000:
            raise ValueError("Maximum 5000 points")
        return self
