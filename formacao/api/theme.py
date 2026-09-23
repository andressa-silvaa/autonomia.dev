from __future__ import annotations

from formacao.ui_palette import BODY_FONT, DARK_THEME, HEADING_FONT, LIGHT_THEME, MONO_FONT


def _declarations(tokens: dict[str, str]) -> str:
    return "\n".join(f"  --{name}: {value};" for name, value in tokens.items())


def build_tokens_css() -> str:
    fonts = {"font-heading": HEADING_FONT, "font-body": BODY_FONT, "font-mono": MONO_FONT}
    light = _declarations(LIGHT_THEME | fonts)
    dark = _declarations(DARK_THEME)
    return (
        f":root {{\n{light}\n  color-scheme: light;\n}}\n"
        "@media (prefers-color-scheme: dark) {\n"
        f'  :root:not([data-theme="light"]) {{\n{dark}\n  color-scheme: dark;\n  }}\n'
        "}\n"
        f':root[data-theme="dark"] {{\n{dark}\n  color-scheme: dark;\n}}\n'
    )
