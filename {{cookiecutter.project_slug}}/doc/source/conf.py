import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import {{cookiecutter.package_name}}

project = {{cookiecutter.package_name}}.__title__
copyright = {{cookiecutter.package_name}}.__copyright__
author = {{cookiecutter.package_name}}.__author__
release = {{cookiecutter.package_name}}.__version__

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx_tabs.tabs",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/{{cookiecutter.github_owner}}/{{cookiecutter.project_slug}}/",
    "source_branch": "main",
    "source_directory": "doc/source",
}

html_static_path = ["_static"]

todo_include_todos = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

linkcheck_allow_redirects = True
