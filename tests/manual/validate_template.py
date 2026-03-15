#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


CHECK_STEPS = ("precommit", "lint", "pytest", "docs", "build")
STEP_ORDER = ("copy", "install", *CHECK_STEPS)
DEFAULT_PROJECT_NAME = "Template Validation"
DEFAULT_PYTHON_VERSION = "3.12"
DEFAULT_PYTEST_TARGET = "tests"
MANUAL_PRECOMMIT_SKIP = "ruff,ruff-format,mypy"


@dataclass
class StepResult:
    name: str
    commands: list[str]
    cwd: str
    log_path: str
    started_at: str
    finished_at: str
    duration_seconds: float
    returncode: int
    status: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def timestamp_slug() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def slugify_project_name(project_name: str) -> str:
    normalized = "-".join(project_name.strip().lower().split())
    return normalized or "template-validation"


def package_name_from_slug(project_slug: str) -> str:
    return project_slug.replace("-", "_")


def command_display(command: list[str]) -> str:
    return shlex.join(command)


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "copier.yml").exists() and (candidate / "template").is_dir():
            return candidate

    raise RuntimeError("Unable to locate the template repository root from this script location.")


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = find_repo_root(SCRIPT_PATH.parent)
DEFAULT_REPORT_ROOT = REPO_ROOT / ".template-validation" / "reports"
DEFAULT_WORKSPACE_ROOT = REPO_ROOT / ".template-validation" / "workspaces"


def default_run_id(project_slug: str) -> str:
    return f"{timestamp_slug()}-{project_slug}"


def resolve_copier_command() -> list[str]:
    if shutil.which("copier"):
        return [shutil.which("copier") or "copier"]

    raise RuntimeError("Copier is not available on PATH.")


def read_python_version(python_command: str) -> str:
    completed = subprocess.run(
        [python_command, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def resolve_python_command(requested_version: str = DEFAULT_PYTHON_VERSION) -> tuple[str, str]:
    candidates = [f"python{requested_version}", sys.executable, "python3", "python"]
    tried: set[str] = set()

    for candidate in candidates:
        if candidate in tried:
            continue
        tried.add(candidate)

        resolved = shutil.which(candidate) if Path(candidate).name == candidate else candidate
        if not resolved:
            continue

        try:
            version = read_python_version(resolved)
        except (OSError, subprocess.CalledProcessError):
            continue

        if version == requested_version:
            return resolved, version

    raise RuntimeError(
        f"Unable to find a Python interpreter for {requested_version}. "
        "Install it locally or update DEFAULT_PYTHON_VERSION in the script."
    )


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_data_file(data_file: Path, project_name: str) -> None:
    data = {"project_name": project_name}
    data_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def run_step(name: str, commands: list[list[str]], cwd: Path, log_path: Path) -> StepResult:
    started = utc_now()
    start = time.monotonic()
    returncode = 0
    status = "passed"

    with log_path.open("w", encoding="utf-8") as log_handle:
        for command in commands:
            log_handle.write(f"$ {command_display(command)}\n")
            log_handle.flush()

            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                log_handle.write(line)
            process.wait()

            if process.returncode != 0:
                returncode = process.returncode
                status = "failed"
                break

            log_handle.write("\n")

    finished = utc_now()
    return StepResult(
        name=name,
        commands=[command_display(command) for command in commands],
        cwd=str(cwd),
        log_path=str(log_path),
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=round(time.monotonic() - start, 3),
        returncode=returncode,
        status=status,
    )


def build_commands(
    copier_command: list[str],
    answers_file: Path,
    workspace_root: Path,
    python_command: str,
    venv_path: Path,
    package_name: str,
    pytest_target: str,
) -> dict[str, list[list[str]]]:
    venv_name = venv_path.name

    return {
        "copy": [
            [
                *copier_command,
                "copy",
                "--trust",
                "--defaults",
                "--data-file",
                str(answers_file),
                str(REPO_ROOT),
                str(workspace_root),
            ]
        ],
        "install": [["make", "install", f"VENV={venv_name}", f"PYTHON={python_command}"]],
        "precommit": [[
            "make",
            "precommit",
            f"VENV={venv_name}",
            f"PRE_COMMIT_SKIP={MANUAL_PRECOMMIT_SKIP}",
        ]],
        "lint": [["make", "lint", f"VENV={venv_name}"]],
        "pytest": [["make", "test", f"VENV={venv_name}", f"TEST_ARGS={pytest_target} -v"]],
        "docs": [["make", "docs", f"VENV={venv_name}"]],
        "build": [["make", "build", f"VENV={venv_name}"]],
    }


def resolve_selected_steps(args: argparse.Namespace) -> list[str]:
    if args.copy_only:
        return ["copy"]

    selected_checks = list(dict.fromkeys(args.run)) if args.run else list(CHECK_STEPS)
    if "precommit" in selected_checks and "lint" not in selected_checks:
        insert_at = selected_checks.index("precommit") + 1
        selected_checks.insert(insert_at, "lint")
    return ["copy", "install", *selected_checks]


def summarize_step(step: dict[str, object]) -> str:
    status = "PASS" if step["status"] == "passed" else "FAIL"
    return (
        f"- [{status}] {step['name']} "
        f"({step['duration_seconds']}s, exit={step['returncode']})"
    )


def build_summary_lines(report: dict[str, object]) -> list[str]:
    overall = "PASS" if report["success"] else "FAIL"
    lines = [
        f"Overall result: {overall}",
        f"Project name: {report['project_name']}",
        f"Project slug: {report['project_slug']}",
        f"Run id: {report['run_id']}",
        "",
        "Steps:",
    ]

    for step in report["steps"]:
        lines.append(summarize_step(step))

    if report["failed_step"]:
        lines.extend(
            [
                "",
                f"Failed step: {report['failed_step']}",
                f"Failing log: {report['failed_log_path']}",
            ]
        )

    lines.extend(
        [
            "",
            f"Quick report: {report['summary_path']}",
            f"Detailed report: {report['markdown_report_path']}",
            f"Machine report: {report['json_report_path']}",
            f"Logs directory: {report['logs_root']}",
        ]
    )
    return lines


def build_markdown_report(report: dict[str, object]) -> str:
    lines = [
        "# Template validation",
        "",
        "## Summary",
        "",
        *build_summary_lines(report),
        "",
        "## Details",
        "",
        f"- Workspace root: `{report['workspace_root']}`",
        f"- Project root: `{report['project_root']}`",
        f"- Python command: `{report['python_command']}`",
        f"- Python version: `{report['python_version']}`",
        f"- Copier command: `{report['copier_command']}`",
        f"- Selected steps: `{', '.join(report['selected_steps'])}`",
        f"- Pytest target: `{report['pytest_target']}`",
        f"- Cleanup performed: `{report['cleanup']['performed']}`",
        f"- Project kept: `{report['cleanup']['kept']}`",
    ]

    lines.extend(["", "## Step Details", ""])
    for step in report["steps"]:
        lines.extend(
            [
                f"### {step['name']}",
                f"- Status: `{step['status']}`",
                f"- Duration: `{step['duration_seconds']}` seconds",
                f"- Exit code: `{step['returncode']}`",
                f"- Working directory: `{step['cwd']}`",
                f"- Log: `{step['log_path']}`",
                "- Commands:",
            ]
        )
        for command in step["commands"]:
            lines.append(f"  - `{command}`")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_reports(report_root: Path, report: dict[str, object]) -> tuple[Path, Path, Path]:
    ensure_directory(report_root)
    summary_path = report_root / "summary.txt"
    json_path = report_root / "report.json"
    markdown_path = report_root / "report.md"

    report["summary_path"] = str(summary_path)
    report["json_report_path"] = str(json_path)
    report["markdown_report_path"] = str(markdown_path)

    summary_path.write_text("\n".join(build_summary_lines(report)) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(build_markdown_report(report), encoding="utf-8")
    return summary_path, json_path, markdown_path


def cleanup_project(project_root: Path, workspace_root: Path, keep_project: bool) -> dict[str, object]:
    cleanup: dict[str, object] = {
        "performed": False,
        "kept": keep_project,
        "project_removed": False,
        "workspace_removed": False,
        "error": None,
    }

    if keep_project:
        return cleanup

    try:
        if project_root.exists():
            shutil.rmtree(project_root)
            cleanup["performed"] = True
            cleanup["project_removed"] = True

        if workspace_root.exists() and not any(workspace_root.iterdir()):
            workspace_root.rmdir()
            cleanup["workspace_removed"] = True
    except OSError as exc:
        cleanup["error"] = str(exc)

    return cleanup


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the generated Copier project using the template defaults.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--project-name",
        default=DEFAULT_PROJECT_NAME,
        help="Human-readable project name passed to Copier.",
    )
    parser.add_argument(
        "--keep-project",
        action="store_true",
        help="Keep the generated project instead of removing it at the end.",
    )
    parser.add_argument(
        "--copy-only",
        action="store_true",
        help="Only render the project and stop before installing dependencies or running checks.",
    )
    parser.add_argument(
        "--run",
        action="append",
        choices=CHECK_STEPS,
        help="Run only selected checks. Pass multiple times to combine checks.",
    )
    parser.add_argument(
        "--pytest-target",
        default=DEFAULT_PYTEST_TARGET,
        help="Pytest path or node id to run when pytest is selected.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        project_name = args.project_name
        project_slug = slugify_project_name(project_name)
        package_name = package_name_from_slug(project_slug)
        selected_steps = resolve_selected_steps(args)
        run_id = default_run_id(project_slug)
        report_root = ensure_directory(DEFAULT_REPORT_ROOT / run_id)
        logs_root = ensure_directory(report_root / "logs")
        workspace_root = ensure_directory(DEFAULT_WORKSPACE_ROOT / run_id)
        project_root = workspace_root / project_slug
        venv_path = project_root / ".venv-template-validation"
        answers_file = report_root / "copier-answers.json"
        write_data_file(answers_file, project_name)

        copier_command = resolve_copier_command()
        python_command, python_version = resolve_python_command()
        commands = build_commands(
            copier_command=copier_command,
            answers_file=answers_file,
            workspace_root=workspace_root,
            python_command=python_command,
            venv_path=venv_path,
            package_name=package_name,
            pytest_target=args.pytest_target,
        )

        print(f"Repository root: {REPO_ROOT}")
        print(f"Project name: {project_name}")
        print(f"Project slug: {project_slug}")
        print(f"Report directory: {report_root}")
        print(f"Checks: {', '.join(selected_steps[2:]) if len(selected_steps) > 2 else 'copy only'}")

        step_results: list[StepResult] = []
        overall_success = True
        failed_step: str | None = None
        failed_log_path: str | None = None
        for index, step in enumerate(selected_steps, start=1):
            cwd = workspace_root if step == "copy" else project_root
            log_path = logs_root / f"{index:02d}-{step}.log"
            print(f"\n==> {step}")
            result = run_step(step, commands[step], cwd=cwd, log_path=log_path)
            step_results.append(result)

            if result.status != "passed":
                overall_success = False
                failed_step = result.name
                failed_log_path = result.log_path
                break

        cleanup = cleanup_project(project_root, workspace_root, args.keep_project)
        report: dict[str, object] = {
            "run_id": run_id,
            "success": overall_success,
            "project_name": project_name,
            "project_slug": project_slug,
            "package_name": package_name,
            "selected_steps": selected_steps,
            "pytest_target": args.pytest_target,
            "workspace_root": str(workspace_root),
            "project_root": str(project_root),
            "report_root": str(report_root),
            "logs_root": str(logs_root),
            "copier_command": command_display(copier_command),
            "python_command": python_command,
            "python_version": python_version,
            "template_root": str(REPO_ROOT),
            "answers_file": str(answers_file),
            "failed_step": failed_step,
            "failed_log_path": failed_log_path,
            "steps": [asdict(step) for step in step_results],
            "cleanup": cleanup,
            "started_at": step_results[0].started_at if step_results else utc_now().isoformat(),
            "finished_at": utc_now().isoformat(),
        }
        summary_path, json_report, markdown_report = write_reports(report_root, report)

        print("\nSummary")
        for line in build_summary_lines(report):
            print(line)
        print(f"\nSummary file: {summary_path}")
        print(f"Detailed report: {markdown_report}")
        print(f"Machine report: {json_report}")

        return 0 if overall_success else 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
