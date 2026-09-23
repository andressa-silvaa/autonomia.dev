from __future__ import annotations

from markdown_it import MarkdownIt

_renderer = MarkdownIt("commonmark", {"html": False}).enable("table")


def render_markdown(text: str) -> str:
    return _renderer.render(text)
