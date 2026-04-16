#!/usr/bin/env python3

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROJECT_NAME = "My Template Sandbox Library"
DEFAULT_PROJECT_SLUG = "my-template-sandbox-library"
DEFAULT_PACKAGE_NAME = "my_template_sandbox_library"
SANDBOX_STATE_FILENAME = ".template-sandbox.json"
IGNORED_DIRECTORIES = {
    ".eggs",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "site-packages",
}


@dataclass(frozen=True)
class SandboxConfig:
    repo_root: Path
    sandbox_dir: Path
    project_name: str
    project_slug: str
    package_name: str

    @property
    def sandbox_project_root(self) -> Path:
        return self.sandbox_dir / self.project_slug

    @property
    def state_file(self) -> Path:
        return self.sandbox_dir / SANDBOX_STATE_FILENAME

    def as_state(self) -> dict[str, str]:
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "package_name": self.package_name,
        }


@dataclass(frozen=True)
class PythonChange:
    relative_path: Path
    sandbox_path: Path
    baseline_path: Path
    template_path: Path
    status: str
    sandbox_diff: str
    template_diff: str


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "copier.yml").exists() and (candidate / "template").is_dir():
            return candidate
    raise RuntimeError("Unable to locate the template repository root.")


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = find_repo_root(SCRIPT_PATH.parent)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render the Copier template into a local sandbox and sync Python-only "
            "changes back into the Jinja template."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export",
        help="Render the template into .sandbox/ using stable sandbox names.",
    )
    add_shared_arguments(export_parser)
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing sandbox project if it already exists.",
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Show Python files that changed in the sandbox compared with a fresh render.",
    )
    add_shared_arguments(status_parser)
    status_parser.add_argument(
        "--diff",
        action="store_true",
        help="Print unified diffs against a fresh sandbox render.",
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Sync Python changes from the sandbox back into template/.",
    )
    add_shared_arguments(import_parser)
    import_parser.add_argument(
        "--diff",
        action="store_true",
        help="Print unified diffs for the template files that will be updated.",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the template updates without writing files.",
    )

    return parser


def add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--sandbox-dir",
        type=Path,
        default=REPO_ROOT / ".sandbox",
        help="Sandbox workspace directory. Defaults to .sandbox/ in the repository root.",
    )
    parser.add_argument(
        "--project-name",
        help=f"Rendered sandbox project name. Defaults to {DEFAULT_PROJECT_NAME!r}.",
    )
    parser.add_argument(
        "--project-slug",
        help=f"Rendered sandbox project slug. Defaults to {DEFAULT_PROJECT_SLUG!r}.",
    )
    parser.add_argument(
        "--package-name",
        help=f"Rendered sandbox Python package name. Defaults to {DEFAULT_PACKAGE_NAME!r}.",
    )


def read_state_file(state_file: Path) -> dict[str, str]:
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def resolve_config(args: argparse.Namespace) -> SandboxConfig:
    sandbox_dir = args.sandbox_dir.resolve()
    state = read_state_file(sandbox_dir / SANDBOX_STATE_FILENAME)
    project_name = args.project_name or state.get("project_name") or DEFAULT_PROJECT_NAME
    project_slug = args.project_slug or state.get("project_slug") or DEFAULT_PROJECT_SLUG
    package_name = args.package_name or state.get("package_name") or DEFAULT_PACKAGE_NAME
    return SandboxConfig(
        repo_root=REPO_ROOT,
        sandbox_dir=sandbox_dir,
        project_name=project_name,
        project_slug=project_slug,
        package_name=package_name,
    )


def resolve_copier_command() -> list[str]:
    copier_path = shutil.which("copier")
    if copier_path:
        return [copier_path]
    raise RuntimeError("Copier is not available on PATH.")


def run_command(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=str(cwd), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def write_answers_file(path: Path, config: SandboxConfig) -> None:
    answers = {
        "project_name": config.project_name,
        "project_slug": config.project_slug,
        "package_name": config.package_name,
    }
    path.write_text(json.dumps(answers, indent=2, sort_keys=True), encoding="utf-8")


def export_sandbox(config: SandboxConfig, force: bool) -> None:
    sandbox_project_root = config.sandbox_project_root
    if sandbox_project_root.exists():
        if not force:
            raise RuntimeError(
                f"Sandbox project already exists at {sandbox_project_root}. "
                "Use --force to replace it."
            )
        shutil.rmtree(sandbox_project_root)

    config.sandbox_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="template-sandbox-answers-") as temp_dir:
        answers_file = Path(temp_dir) / "answers.json"
        write_answers_file(answers_file, config)
        command = [
            *resolve_copier_command(),
            "copy",
            "--trust",
            "--defaults",
            "--data-file",
            str(answers_file),
            str(config.repo_root),
            str(config.sandbox_dir),
        ]
        run_command(command, config.repo_root)

    config.state_file.write_text(json.dumps(config.as_state(), indent=2, sort_keys=True), encoding="utf-8")

    print(f"Sandbox created at: {sandbox_project_root}")
    print(f"State file written to: {config.state_file}")
    print(f"Next step: cd {sandbox_project_root}")


def iter_python_files(project_root: Path) -> list[Path]:
    python_files: list[Path] = []
    for path in project_root.rglob("*.py"):
        relative_path = path.relative_to(project_root)
        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue
        python_files.append(path)
    return sorted(python_files)


def render_baseline_project(config: SandboxConfig) -> tuple[Path, Path]:
    baseline_root = Path(tempfile.mkdtemp(prefix="template-sandbox-baseline-"))
    answers_file = baseline_root / "answers.json"
    workspace_root = baseline_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    write_answers_file(answers_file, config)
    command = [
        *resolve_copier_command(),
        "copy",
        "--trust",
        "--defaults",
        "--data-file",
        str(answers_file),
        str(config.repo_root),
        str(workspace_root),
    ]
    try:
        run_command(command, config.repo_root)
    except Exception:
        shutil.rmtree(baseline_root, ignore_errors=True)
        raise
    return baseline_root / "workspace" / config.project_slug, baseline_root


def replace_sandbox_names_with_template_tokens(text: str, config: SandboxConfig) -> str:
    replacements = [
        (config.project_name, "{{ project_name }}"),
        (config.package_name, "{{ package_name }}"),
        (config.project_slug, "{{ project_slug }}"),
    ]
    updated = text
    for concrete, token in replacements:
        updated = updated.replace(concrete, token)
    return updated


def map_sandbox_path_to_template(relative_path: Path, config: SandboxConfig) -> Path:
    rendered_parts = []
    for part in relative_path.parts:
        updated = part.replace(config.package_name, "{{ package_name }}")
        updated = updated.replace(config.project_slug, "{{ project_slug }}")
        rendered_parts.append(updated)
    return Path("template") / "{{ project_slug }}" / Path(*rendered_parts)


def build_unified_diff(before_text: str, after_text: str, before_label: str, after_label: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile=before_label,
            tofile=after_label,
            lineterm="",
        )
    )


def collect_python_changes(config: SandboxConfig, baseline_project_root: Path) -> list[PythonChange]:
    sandbox_project_root = config.sandbox_project_root
    if not sandbox_project_root.exists():
        raise RuntimeError(
            f"Sandbox project does not exist at {sandbox_project_root}. Run the export command first."
        )

    changes: list[PythonChange] = []

    for sandbox_path in iter_python_files(sandbox_project_root):
        relative_path = sandbox_path.relative_to(sandbox_project_root)
        baseline_path = baseline_project_root / relative_path
        sandbox_text = sandbox_path.read_text(encoding="utf-8")
        baseline_text = baseline_path.read_text(encoding="utf-8") if baseline_path.exists() else ""

        if baseline_path.exists() and sandbox_text == baseline_text:
            continue

        template_path = config.repo_root / map_sandbox_path_to_template(relative_path, config)
        status = "new" if not baseline_path.exists() else "modified"
        template_text = replace_sandbox_names_with_template_tokens(sandbox_text, config)
        existing_template_text = template_path.read_text(encoding="utf-8") if template_path.exists() else ""
        changes.append(
            PythonChange(
                relative_path=relative_path,
                sandbox_path=sandbox_path,
                baseline_path=baseline_path,
                template_path=template_path,
                status=status,
                sandbox_diff=build_unified_diff(
                    baseline_text,
                    sandbox_text,
                    str(baseline_path if baseline_path.exists() else Path("/dev/null")),
                    str(relative_path),
                ),
                template_diff=build_unified_diff(
                    existing_template_text,
                    template_text,
                    str(template_path if template_path.exists() else Path("/dev/null")),
                    str(template_path),
                ),
            )
        )

    return changes


def print_change_summary(changes: list[PythonChange], config: SandboxConfig) -> None:
    if not changes:
        print("No Python changes detected in the sandbox.")
        return

    print(f"Detected {len(changes)} Python change(s):")
    for change in changes:
        print(f"- [{change.status}] {change.relative_path} -> {change.template_path.relative_to(config.repo_root)}")


def show_status(config: SandboxConfig, show_diff: bool) -> int:
    baseline_project_root, cleanup_root = render_baseline_project(config)
    try:
        changes = collect_python_changes(config, baseline_project_root)
    finally:
        shutil.rmtree(cleanup_root, ignore_errors=True)

    print_change_summary(changes, config)
    if show_diff:
        for change in changes:
            print()
            print(change.sandbox_diff or f"No diff generated for {change.relative_path}")
    return 0


def import_changes(config: SandboxConfig, show_diff: bool, dry_run: bool) -> int:
    baseline_project_root, cleanup_root = render_baseline_project(config)
    try:
        changes = collect_python_changes(config, baseline_project_root)
    finally:
        shutil.rmtree(cleanup_root, ignore_errors=True)

    print_change_summary(changes, config)
    if not changes:
        return 0

    for change in changes:
        rendered_text = replace_sandbox_names_with_template_tokens(
            change.sandbox_path.read_text(encoding="utf-8"),
            config,
        )
        if show_diff:
            print()
            print(change.template_diff or f"No diff generated for {change.template_path}")
        if dry_run:
            continue
        change.template_path.parent.mkdir(parents=True, exist_ok=True)
        change.template_path.write_text(rendered_text, encoding="utf-8")

    if dry_run:
        print("Dry run only. No template files were modified.")
    else:
        print("Template files updated from the sandbox.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    config = resolve_config(args)

    try:
        if args.command == "export":
            export_sandbox(config, force=args.force)
            return 0
        if args.command == "status":
            return show_status(config, show_diff=args.diff)
        if args.command == "import":
            return import_changes(config, show_diff=args.diff, dry_run=args.dry_run)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
