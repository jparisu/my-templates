# {{ project_name }}

`{{ project_name }}` is a Python project scaffolded from this template.

## Features

- Modern `src/`-layout packaging
- Ruff, mypy, pytest, coverage, and pre-commit
- MkDocs + mkdocstrings documentation
{% if include_cli %}
- Optional CLI entrypoint: `{{ project_slug }}`
{% endif %}
{% if include_utils %}
- Shared utils integration placeholder enabled in the template
{% endif %}

## Installation

From Git:

```bash
python -m pip install "git+{{ repo_url }}.git"
```

From a local checkout:

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

## Quick Start

```python
import {{ package_name }}

print({{ package_name }}.__version__)
```

{% if include_cli %}
CLI usage:

```bash
{{ project_slug }} --help
```
{% endif %}

## Development

Useful commands:

```bash
make install
make install-current
make lint
make test
make docs
```

## License

Licensed under the Apache 2.0 License.
