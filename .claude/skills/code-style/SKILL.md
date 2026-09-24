---
name: code-style
description: Mandatory code style rules for this project. Use before writing, editing or reviewing ANY code or config file in this repository (Python, SQL, YAML, TOML, JS, HTML, CSS, shell, .env files, tests). Enforces English-only code and a ban on comments and docstrings unless the user explicitly authorizes each one.
---

# Code style rules

These rules apply to every file you create or edit in this repository.

## 1. All code is written in English

- Identifiers (variables, functions, classes, modules, files, folders, tables, columns, enum values, test names, migration names, environment variables, CLI command names) must be in English.
- Log messages, exception messages and developer-facing strings are in English.
- Folder and file names are in English everywhere, including content in `data/` (e.g. `data/tracks/cs-fundamentals/07-recursion.md`). Content slugs (areas, competencies, tracks, modules) are English identifiers too (e.g. `cs-fundamentals/recursion`).
- The package and CLI are called `hone`; the project/brand name is `autonomia.dev`.
- The only exception is **user-facing text** shown to the person studying (CLI output, help texts, dashboard labels, and the titles, names, descriptions and Markdown body of study content in `data/`). That text stays in Brazilian Portuguese.

## 2. Comments are forbidden

- Do not write comments in any language or file type: `#`, `//`, `/* */`, `--`, `<!-- -->`, `REM`, etc.
- Docstrings count as comments and are also forbidden (modules, classes, functions, tests).
- Commented-out code is forbidden.
- Make code explain itself instead: descriptive names, small functions, named constants, explicit types.
- Where a tool needs descriptive text (e.g. Typer command help, FastAPI endpoint descriptions), pass it as an explicit argument (`help="..."`, `description="..."`), not as a docstring.
- Design rationale belongs in `docs/adr/` or `README.md`, never inside source files.

## 3. When a comment seems necessary

1. Stop. First try to remove the need for it (rename, extract a function, add a named constant).
2. If it is still necessary, **ask the user for authorization** before writing it, showing the exact comment text and the file/line where it would go, and explaining why the code alone cannot express it.
3. Only write the comment after the user explicitly approves that specific comment. Approval does not carry over to other comments.

Functional directives that tools require are not comments and are allowed without authorization: shebangs (`#!/usr/bin/env python`), `# type: ignore`, `# noqa`, encoding declarations and linter pragmas. Use them only when strictly needed.

## 4. Checklist before finishing a change

- [ ] No comment or docstring was added (search the diff for `#`, `//`, `--`, `"""`, `/*`, `<!--`).
- [ ] Every new identifier is in English.
- [ ] User-facing text is in Portuguese.
