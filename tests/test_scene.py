from pathlib import Path
import pytest
from pydantic import ValidationError
from chatgpt_manim.scene import SceneSpec, safe_math


@pytest.fixture
def spec():
    return SceneSpec(
        title="Triangle",
        resolution="480p",
        fps=15,
        objects=[{"id": "a", "kind": "circle"}],
        steps=[{"action": "create", "target": "a", "duration": 0.2}],
    )


@pytest.mark.parametrize("path", list(Path("examples").glob("*.json")))
def test_examples(path):
    assert SceneSpec.model_validate_json(path.read_text())


@pytest.mark.parametrize(
    "text",
    [
        r"\input{/etc/passwd}",
        r"\write18{curl evil}",
        r"\def\x{y}",
        r"\includegraphics{x}",
        r"\csname input\endcsname{x}",
        r"\begin{document}x\end{document}",
        r"^^5cinput{x}",
    ],
)
def test_reject_tex_io(text):
    with pytest.raises(ValueError):
        safe_math(text)


@pytest.mark.parametrize(
    "patch",
    [
        {"pacing": float("nan")},
        {"resolution": "4k"},
        {"source": "import os"},
        {"pacing": 100},
    ],
)
def test_reject_bad_options(spec, patch):
    with pytest.raises(ValidationError):
        SceneSpec.model_validate(spec.model_dump() | patch)


def test_unknown_target(spec):
    data = spec.model_dump()
    data["steps"][0]["target"] = "missing"
    with pytest.raises(ValidationError):
        SceneSpec.model_validate(data)


def test_timeline_limit(spec):
    data = spec.model_dump()
    data["steps"] = [{"action": "wait", "duration": 15}] * 7
    with pytest.raises(ValidationError):
        SceneSpec.model_validate(data)


def test_no_expression_eval(spec):
    data = spec.model_dump()
    data["objects"][0]["kind"] = "function"
    data["objects"][0]["text"] = '__import__("os")'
    with pytest.raises(ValidationError):
        SceneSpec.model_validate(data)
