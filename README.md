# `my-templates`

`my-templates` is a [Copier](https://copier.readthedocs.io/) template repository for bootstrapping modern Python projects.


## Generated Features

- Packaging via `pyproject.toml`. This gives generated projects a modern build backend and metadata layout.
- Quality tooling. Generated projects include Ruff, mypy, pytest, coverage, and pre-commit configuration.
- Documentation tooling. Generated projects include MkDocs and mkdocstrings configuration out of the box.
- `src/` package layout. This keeps importable code isolated from tooling and test files.
- Optional CLI support. When enabled, the generated package exposes a console script entrypoint.
- Optional shared utils placeholder. When enabled, the generated project keeps a documented dependency slot for internal utilities.


## Template Files

- [`copier.yml`](/home/jparisu/projects/devs/my-templates/copier.yml). This is the main Copier configuration, including questions, defaults, user-facing copy/update messages, and the post-render tasks required by the current layout.
- [`{{ _copier_conf.answers_file }}.jinja`](/home/jparisu/projects/devs/my-templates/{{ _copier_conf.answers_file }}.jinja). This documents the intended `.copier-answers.yml` contents that the post-render task writes into generated projects.
- [`template/`](/home/jparisu/projects/devs/my-templates/template). This contains the generated project skeleton and should stay focused on rendered project files.


## Requirements

- Copier 9 or newer. The root configuration uses current Copier settings such as `_subdirectory`, `_answers_file`, and `_templates_suffix`.
- Trusted task execution. This template uses post-render tasks to restore the generated project's GitHub workflow files, rename `README.md.jinja`, and write `.copier-answers.yml` because the render root is `template/` and most template files are rendered in place.
- Git access to this repository. Updating generated projects works best when they were created from a git-backed template source.


## Copy A Project

Use a git-backed source when you want future `copier update` runs to track template revisions automatically.

```bash
# Generate a new project from the local checkout of this template repository.
copier copy --trust --vcs-ref main git+https://github.com/jparisu/my-templates.git ./my-new-project

# Move into the generated project directory.
cd ./my-new-project

# Create new virtual environment and install development dependencies for linting, testing, and docs work.
make install
```


### Git Initialization

If the new project is meant to be a git repository, initialize it after copying.

```bash
# Initialize git in the generated project directory.
# NOTE: this command will show an error while no commit exists.
git init

# Add all files and make the initial commit.
# NOTE: this command will show an error while no commit exists.
git add .

# Create the initial commit with a message.
git commit -m "Initial commit from my-templates"

# Optionally, upload it to github
gh repo create my-new-project --public --source=. --remote=origin --push
```


## Update A Generated Project

Generated projects should keep `.copier-answers.yml` committed. That file records the template source and the answers that Copier needs to replay the template safely.

```bash
# Move into an existing project that was created from this template.
cd ./my-new-project

# Review local changes before replaying the template.
git status --short

# Re-render the project using the answers stored in .copier-answers.yml.
copier update --trust

# Run the generated project's validation commands after the update.
pre-commit run --all-files
pytest
```

If the template introduces a conflict, resolve it the same way you would resolve a normal git merge conflict and then rerun your validation commands.
