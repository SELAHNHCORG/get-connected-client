#!/usr/bin/env python3
"""Post-generation hook: replace __FIGLET__ in __init__.py with ANSI Shadow ASCII art."""

import os

PROJECT_SLUG = "{{cookiecutter.project_slug}}"
PACKAGE_NAME = "{{cookiecutter.package_name}}"

WIDTH = 88


def centered_art(word):
    try:
        import pyfiglet

        art = pyfiglet.figlet_format(word, font="ansi_shadow").rstrip()
        lines = art.splitlines()
        max_w = max(len(line) for line in lines)
        pad = (WIDTH - max_w) // 2
        return "\n".join(" " * pad + line for line in lines)
    except Exception:
        return word.center(WIDTH)


words = PROJECT_SLUG.split("-")
art_block = "\n\n".join(centered_art(w) for w in words)

init_path = os.path.join("src", PACKAGE_NAME, "__init__.py")
with open(init_path) as f:
    content = f.read()

content = content.replace("__FIGLET__", art_block)

with open(init_path, "w") as f:
    f.write(content)
