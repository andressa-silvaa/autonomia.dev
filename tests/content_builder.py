from __future__ import annotations

from pathlib import Path

SAMPLE_CATALOG = """
[[areas]]
slug = "fundamentos"
name = "Fundamentos"

[[competencies]]
slug = "basico"
area = "fundamentos"
name = "Básico"
"""

SAMPLE_TRACK = """
[track]
slug = "sample"
name = "Trilha de exemplo"
description = "Usada nos testes."

[[modules]]
slug = "first"
title = "Primeiro"
content = "01-first.md"
competencies = ["basico"]

[[modules]]
slug = "second"
title = "Segundo"
content = "02-second.md"
requires = ["first"]

[[modules]]
slug = "third"
title = "Terceiro"
content = "03-third.md"
requires = ["first", "second"]
"""

SAMPLE_FILES = ("01-first.md", "02-second.md", "03-third.md")


def write_content(
    root: Path, catalog: str = SAMPLE_CATALOG, tracks: dict[str, str] | None = None
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "catalog.toml").write_text(catalog, encoding="utf-8")
    for slug, track_toml in (tracks if tracks is not None else {"sample": SAMPLE_TRACK}).items():
        track_dir = root / "tracks" / slug
        track_dir.mkdir(parents=True, exist_ok=True)
        (track_dir / "track.toml").write_text(track_toml, encoding="utf-8")
        for name in SAMPLE_FILES:
            (track_dir / name).write_text(
                f"# {name}\n\nConteúdo de **{name}**.\n", encoding="utf-8"
            )
    return root
