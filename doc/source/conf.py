"""Sphinx configuration for get-connected-client.

Runs against the *installed* package (see ``just build-docs-html``), so
autodoc imports it directly rather than manipulating ``sys.path``.
"""

from __future__ import annotations

import get_connected_client

project = get_connected_client.__title__
author = get_connected_client.__author__
copyright = get_connected_client.__copyright__
release = get_connected_client.__version__
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinxcontrib.typer",
]

# Kept to just Python: httpx/pydantic inventories are optional and flaky to
# depend on for link resolution.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = False

# `Resource._parse`/`_get_one` (resources/base.py) annotate a parameter as
# `type[GalaxyModel]`, using the builtin `type`. Several pydantic models
# also have a field literally named `type` (it mirrors an API field name).
# Autodoc's signature renderer cross-references the builtin `type` by bare
# name, which collides with those fields under the same domain, producing
# an unresolvable "more than one target" warning that reflects a real
# object naming collision rather than a broken reference.
suppress_warnings = ["ref.python"]

html_static_path = ['_static']
html_css_files = ['style.css']

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/django-commons/django-typer/",
    "source_branch": "main",
    "source_directory": "doc/source",
}
html_title = f"{project} {release}"


def pypi_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    from docutils import nodes

    url = f"https://pypi.org/project/{text}/"
    node = nodes.reference(rawtext, text, refuri=url, **options)
    return [node], []


def setup(app):
    from docutils.parsers.rst import roles

    # app.connect('html-page-context', add_page_class)
    roles.register_local_role("pypi", pypi_role)
