from __future__ import annotations

from pathlib import Path

SAMPLE_CATALOG = """
[[areas]]
slug = "fundamentals"
name = "Fundamentos"

[[competencies]]
slug = "basics"
area = "fundamentals"
name = "Básico"

[[competencies]]
slug = "advanced"
area = "fundamentals"
name = "Avançado"
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
competencies = ["basics"]

[[modules]]
slug = "second"
title = "Segundo"
content = "02-second.md"
requires = ["first"]
competencies = ["advanced"]

[[modules]]
slug = "third"
title = "Terceiro"
content = "03-third.md"
requires = ["first", "second"]
"""

SAMPLE_DIAGNOSTICS = """
[[questions]]
slug = "basics-concept"
competency = "basics"
kind = "concept"
prompt = "Qual é a certa?"
options = ["certa", "errada"]
answer = 1
explanation = "Porque sim."

[[questions]]
slug = "basics-code"
competency = "basics"
kind = "code_reading"
prompt = "Quanto dá `1 + 1`?"
accept = ["2"]

[[questions]]
slug = "advanced-concept"
competency = "advanced"
kind = "concept"
prompt = "E agora?"
options = ["sim", "não"]
answer = 2
"""

SAMPLE_FILES = ("01-first.md", "02-second.md", "03-third.md")


def write_content(
    root: Path,
    catalog: str = SAMPLE_CATALOG,
    tracks: dict[str, str] | None = None,
    diagnostics: str | None = SAMPLE_DIAGNOSTICS,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "catalog.toml").write_text(catalog, encoding="utf-8")
    if diagnostics is not None:
        diagnostics_dir = root / "diagnostics"
        diagnostics_dir.mkdir(exist_ok=True)
        (diagnostics_dir / "sample.toml").write_text(diagnostics, encoding="utf-8")
    for slug, track_toml in (tracks if tracks is not None else {"sample": SAMPLE_TRACK}).items():
        track_dir = root / "tracks" / slug
        track_dir.mkdir(parents=True, exist_ok=True)
        (track_dir / "track.toml").write_text(track_toml, encoding="utf-8")
        for name in SAMPLE_FILES:
            (track_dir / name).write_text(
                f"# {name}\n\nConteúdo de **{name}**.\n", encoding="utf-8"
            )
    return root


SAMPLE_EXERCISES = {
    "first/pick-right": {
        "exercise.toml": """
title = "Escolha a certa"
kind = "quiz"
grading = "auto"
difficulty = 2
required = true
options = ["certa", "errada"]
answer = 1
hints = ["primeira dica", "segunda dica"]
""",
        "README.md": "Qual é a certa?",
    },
    "first/double-it": {
        "exercise.toml": """
title = "Dobrar"
kind = "code"
grading = "auto"
difficulty = 2
""",
        "README.md": "Implemente `double(n)`.",
        "starter.py": "def double(n):\n    raise NotImplementedError\n",
        "test_solution.py": (
            "from solution import double\n\n\ndef test_doubles():\n    assert double(2) == 4\n"
        ),
    },
    "second/explain-it": {
        "exercise.toml": """
title = "Explique"
kind = "explanation"
grading = "ollama"
difficulty = 2
rubric = ["cita o primeiro ponto", "cita o segundo ponto"]
""",
        "README.md": "Explique os dois pontos.",
        "reference.md": "Uma resposta de referência.",
    },
    "second/self-check": {
        "exercise.toml": """
title = "Confira sozinha"
kind = "explanation"
grading = "self"
difficulty = 1
rubric = ["critério um", "critério dois", "critério três"]
""",
        "README.md": "Escreva sobre três critérios.",
    },
}

PASSING_DOUBLE = "def double(n):\n    return n * 2\n"


def write_exercises(
    root: Path, exercises: dict[str, dict[str, str]] | None = None, track: str = "sample"
) -> Path:
    for relative, files in (exercises if exercises is not None else SAMPLE_EXERCISES).items():
        folder = root / track / relative
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (folder / name).write_text(text, encoding="utf-8")
    return root
