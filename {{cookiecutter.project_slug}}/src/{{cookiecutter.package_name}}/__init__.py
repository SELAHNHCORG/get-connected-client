r"""
::

__FIGLET__

{{cookiecutter.description}}
"""

__title__ = "{{cookiecutter.project_slug}}"
__version__ = "{{cookiecutter.version}}"
__author__ = "{{cookiecutter.author_name}}"
{% if cookiecutter.license == "MIT" %}__license__ = "MIT"
{% elif cookiecutter.license == "Apache" %}__license__ = "Apache-2.0"
{% elif cookiecutter.license == "BSD-3" %}__license__ = "BSD-3-Clause"
{% else %}__license__ = ""
{% endif %}__copyright__ = "Copyright {{cookiecutter.year}} {{cookiecutter.author_name}}"
