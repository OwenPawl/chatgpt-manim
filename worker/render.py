"""Trusted renderer entrypoint. JSON goes in; MP4 bytes come out. No eval/exec."""

import contextlib
from pathlib import Path
import subprocess
import sys
from manim import (
    Scene,
    Text,
    MathTex,
    Circle,
    Rectangle,
    Line,
    Arrow,
    Polygon,
    Axes,
    VMobject,
    Create,
    Write,
    FadeIn,
    FadeOut,
    Rotate,
    Transform,
    Indicate,
    tempconfig,
)
from chatgpt_manim.scene import SceneSpec


def object_for(item):
    p = lambda xy: [xy[0], xy[1], 0]
    kw = {"color": item.color}
    if item.kind == "text":
        obj = Text(item.text, font_size=item.font_size, **kw)
    elif item.kind == "math":
        obj = MathTex(item.text, font_size=item.font_size, **kw)
    elif item.kind == "circle":
        obj = Circle(radius=item.radius, fill_opacity=item.fill_opacity, **kw)
    elif item.kind == "rectangle":
        obj = Rectangle(
            width=item.width, height=item.height, fill_opacity=item.fill_opacity, **kw
        )
    elif item.kind == "line":
        obj = Line(p(item.points[0]), p(item.points[1]), **kw)
    elif item.kind == "arrow":
        obj = Arrow(p(item.points[0]), p(item.points[1]), buff=0, **kw)
    elif item.kind == "polygon":
        obj = Polygon(*map(p, item.points), fill_opacity=item.fill_opacity, **kw)
    elif item.kind == "axes":
        obj = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=item.width,
            y_length=item.height,
            tips=False,
            axis_config=kw,
        )
    elif item.kind == "polyline":
        obj = VMobject(**kw).set_points_as_corners(list(map(p, item.points)))
    else:
        raise ValueError("Unsupported object")
    if item.kind not in ("line", "arrow", "polygon", "polyline"):
        obj.move_to(p(item.position))
    else:
        obj.shift(p(item.position))
    return obj


def render(spec):
    class DeclarativeScene(Scene):
        def construct(self):
            objects = {o.id: object_for(o) for o in spec.objects}
            for step in spec.steps:
                seconds = step.duration * spec.pacing
                if step.action == "wait":
                    self.wait(seconds)
                    continue
                obj = objects[step.target]
                if step.action in ("create", "write", "fade_in", "fade_out"):
                    anim = {
                        "create": Create,
                        "write": Write,
                        "fade_in": FadeIn,
                        "fade_out": FadeOut,
                    }[step.action](obj)
                elif step.action == "move":
                    anim = obj.animate.move_to([*step.position, 0])
                elif step.action == "rotate":
                    anim = Rotate(obj, angle=step.angle)
                elif step.action == "scale":
                    anim = obj.animate.scale(step.factor)
                elif step.action == "color":
                    anim = obj.animate.set_color(step.color)
                elif step.action == "transform":
                    anim = Transform(obj, object_for(step.replacement))
                elif step.action == "indicate":
                    anim = Indicate(obj, color=step.color or "#FFD166")
                self.play(anim, run_time=seconds)

    width, height = {"480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080)}[
        spec.resolution
    ]
    with tempconfig(
        {
            "pixel_width": width,
            "pixel_height": height,
            "frame_rate": spec.fps,
            "background_color": spec.background,
            "media_dir": "/work/media",
            "output_file": "animation",
            "disable_caching": True,
            "write_to_movie": True,
            "format": "mp4",
            "verbosity": "WARNING",
            "tex_dir": "/work/tex",
            "text_dir": "/work/text",
        }
    ):
        scene = DeclarativeScene()
        scene.render()
        output = scene.renderer.file_writer.movie_file_path
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(output),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "23",
            "-movflags",
            "+faststart",
            "-an",
            "/work/result.mp4",
        ],
        check=True,
    )
    result = Path("/work/result.mp4")
    if result.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Output exceeds 32 MiB quota")
    return result.read_bytes()


if __name__ == "__main__":
    raw = sys.stdin.buffer.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024:
        raise ValueError("Input exceeds 256 KiB")
    spec = SceneSpec.model_validate_json(raw)
    with contextlib.redirect_stdout(sys.stderr):
        data = render(spec)
    sys.stdout.buffer.write(data)
