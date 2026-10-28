import json
from pathlib import Path
import jsonschema


def test_official_manifests():
    for name in ("plugin", "mcp"):
        jsonschema.validate(
            json.loads(Path(name + ".json").read_text()),
            json.loads(Path("docs/schemas/" + name + ".schema.json").read_text()),
        )


def test_eval_fixture():
    cases = json.loads(Path("tests/prompts.json").read_text())
    assert {"invoke", "avoid", "revise"} <= {x["expected"] for x in cases}
    assert len({x["prompt"] for x in cases}) == len(cases)
