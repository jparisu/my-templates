# Contributing to {{ project_name }}

## Development setup

1. Create and activate a virtual environment.
2. Clone the repository:

   ```bash
   git clone {{ repo_url }}.git
   cd {{ project_slug }}
   ```

3. Install the project in editable mode:

   ```bash
   python -m pip install -e ".[dev]"
   pre-commit install
   ```

## Useful commands

```bash
make format
make lint
make test
make docs
```

## Pull requests

Please keep pull requests focused, add or update tests when behavior changes, and update the documentation when needed.

## Release notes

Add user-facing changes to `CHANGELOG.md`.
