# AGENTS.md

## Purpose
...

## Restrictions
- NEVER TOUCH ANYTHING OUTSIDE THIS REPOSITORY. You are only allowed to read and modify files within this repository.
- NEVER USE THE INTERNET. You are not allowed to access any external resources, including search engines, APIs, or databases.

## Priorities
When working in this project, keep this order of importance:

1. Pythonic: Ensure readability, maintainability, reusability, and consistency.
2. Code: Prefer correct behavior over stylistic cleanup.
3. Test: Add or update tests for behavior changes.
4. Documentation: Keep user-facing and developer-facing documentation aligned with the code.
5. Format: Apply formatting and lint fixes after correctness is in place.

## Project structure
- Library code lives in `src/`
    - Modules and submodules are named with gerunds (e.g. `utilizing/`).
    - Class names use `CamelCase`.
    - Files defining a class use the same `CamelCase` name as the class and contain only that class by default.
    - Files with shared information only for the model use `_shared.py`.
    - Shared modules without a class use `snake_case` filenames.
    - Functions and methods use `snake_case`.
    - Protected functions and methods start with one leading underscore (`_`).
    - Private functions and methods start with two leading underscores (`__`).
- Tests live in `tests/`
    - Unittest follows same directory structure as `src/`.
    - Each method for each module have at least 2 sweet path tests, 1 edge case test and 1 error case test.
    - Integration tests are organized by feature or module in `tests/integration/`.
    - Human validation tests, such as visual outputs, live in `tests/manual/`.
- Documentation lives in `docs/`
    - Public API docs are generated from docstrings in `src/`.
    - User guides and other public-facing documentation are written in markdown in `docs/`.
    - The documentation will be hosted in ReadTheDocs.
- Design lives in `devs/`
    - `devs/` follows same directory structure as `src/` for design docs related to specific modules.
    - Design artifacts must reference the same naming convention used in `src/`, including `CamelCase` class files, `_shared.py`, and `snake_case` shared modules.
    - Internal text design docs live in markdown files called `.dsg`.
    - Class and sequence diagrams use plantuml.
    - Task files `.tsk` contain specific tasks to be done in module, class and function levels.
- Applications and runnables live in `apps/`
- User helpers live in `resources/`
- Configuration is defined in `pyproject.toml`
- CI workflows live in `.github/workflows/`

## General rules
Rules for code agents to follow. If a rule must be broken, ask for explicit permission:
- Preserve public behavior.
- Re-utilize existing code when possible.
- Follow good-practices for coding, including design patterns and conventions.
- Do not introduce new dependencies without approval.
- Prefer explicit, typed, readable code.
- Avoid refactors.
- Do not write absolute filesystem paths in repository files; use paths relative to the repository root.
- Keep a clean state between the implementation `/src` and the design `/devs` directories.

## New Feature Development policy
1. understand the affected public and internal interfaces
2. add design doc if the change is non-trivial
3. create directories, files and public API before implementing logic
4. add or update tests first when practical
5. implement code required
6. run validation checks
7. update user-facing docs and changelog

## Agents policy
Agents skills are defined under .agents
