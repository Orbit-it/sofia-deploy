from __future__ import annotations

from importlib import resources
from pathlib import Path


def template_text(name: str) -> str:
    return resources.files("sofia").joinpath("templates", name).read_text(encoding="utf-8")


def render_template(name: str, mapping: dict[str, str]) -> str:
    text = template_text(name)
    for key, value in mapping.items():
        text = text.replace(f"__{key}__", value)
    return text


def write_rendered(name: str, dest: Path, mapping: dict[str, str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_template(name, mapping), encoding="utf-8")
