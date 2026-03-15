# Development

## Tooling

- Ruff for linting and formatting
- Mypy for type checking
- Pytest for testing
- MkDocs for documentation

{% if include_utils %}
## Shared utils

This template was generated with shared utils integration enabled. Add the relevant internal dependency in `pyproject.toml` before using it.
{% endif %}

## Commands

```bash
make install
make install-current
make format
make lint
make test
make docs
```
