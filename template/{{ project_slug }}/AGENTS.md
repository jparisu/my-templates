# AGENTS.md

## Priorities
When working in this project, keep this order of importance:

1. Pythonic: Ensure readability, maintainability, reusability, and consistency.
2. Code: Prefer correct behavior over stylistic cleanup.
3. Test: Add or update tests for behavior changes.
4. Documentation: Keep user-facing and developer-facing documentation aligned with the code.
5. Format: Apply formatting and lint fixes after correctness is in place.
6. Size and complexity checks.

## Mode
If one of the following modes are set in the task description, follow the corresponding guidelines:

### `mode:arch`
Use for architecture and design decisions.
- Understand the current structure of the project.
- Modify design documents or diagrams if they exist, or create new ones if needed.
- Create empty folders and files to establish the intended structure, but avoid adding implementation details until the design is finalized.

### `mode:dev`
Use for design and development of new features or significant refactors.
- Read the relevant code before editing.
- Check previous implementations, classes and functions that may be re-used.
- Update or add tests that capture the intended behavior and confirm the implementation.
- Write down the code implementation with clear comments and docstrings.

### `mode:fix`
Use for fixing bugs, errors, or unintended behavior.
- Read the relevant code before editing.
- Update or add tests that capture the issue and confirm the error.
- Make the smallest coherent change that solves the task.
- Update documentation when behavior, APIs, or workflows change.

### `mode:check`
Use for validation and review.
- Run the relevant test suite: `make test`.
- Run formatting and lint checks: `pre-commit run`.

### `mode:query`
Use for questions, exploration, and explanation.
- Do not edit files unless explicitly asked.
- Ground answers in the current repository state.
- Point to the exact files that define the behavior being discussed.

### `mode:docs`
Use for documentation-specific tasks.
- Prefer existing terminology from the codebase.
- Keep examples accurate and minimal.
- Update nearby documentation instead of creating duplicate guidance.

## Project Guidelines
Use these files for contribution and maintenance guidance:
- `README.md`: primary project overview, setup, and common usage.
- `CONTRIBUTING.md`: contribution workflow and repository conventions.
