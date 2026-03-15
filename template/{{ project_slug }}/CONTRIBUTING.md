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

## Project structure

- `src/{{ project_slug }}/`: main source code for the project.
- `tests/`: test suite for the project.
- `docs/`: documentation for the project.
- `apps/`: example applications and demos using the project.

### Format conventions

#### Code

- Classes would use `PascalCase`.
- Functions and variables would use `snake_case`.
- Constants would use `UPPER_SNAKE_CASE`.

#### Files and directories

- Directories would use gerund `.ing` form.
- If a file contains a single class, it would be named after the class.
- If a file contains multiple classes or functions, it would be named after the main functionality it provides.
- Use single files for each class or closely related classes.

#### Python

- Use typing annotations for all function signatures.
- Use complete docstrings.
- Use max line, max file and complexity checks to maintain readability and simplicity.
