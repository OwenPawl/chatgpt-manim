import asyncio
from pathlib import Path
from chatgpt_manim.scene import SceneSpec
from chatgpt_manim.renderer import ContainerRenderer


async def main():
    for file in Path("examples").glob("*.json"):
        print(f"Rendering {file.name}", flush=True)
        await ContainerRenderer().render(
            SceneSpec.model_validate_json(file.read_text()),
            Path("assets") / (file.stem + ".mp4"),
        )
        print(f"Rendered {file.name}", flush=True)


asyncio.run(main())
