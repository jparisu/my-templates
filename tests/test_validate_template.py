import importlib.util
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "manual" / "validate_template.py"
SPEC = importlib.util.spec_from_file_location("validate_template", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
validate_template = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_template
SPEC.loader.exec_module(validate_template)


def parse_args(*argv: str):
    return validate_template.create_parser().parse_args(list(argv))


def test_parser_exposes_small_public_cli() -> None:
    parser = validate_template.create_parser()
    actions = [action.dest for action in parser._actions]

    assert actions == ["help", "project_name", "keep_project", "copy_only", "run", "pytest_target"]


def test_parser_uses_documented_default_project_name() -> None:
    args = parse_args()

    assert args.project_name == validate_template.DEFAULT_PROJECT_NAME


def test_default_selected_steps_run_full_validation() -> None:
    args = parse_args()

    assert validate_template.resolve_selected_steps(args) == [
        "copy",
        "install",
        "precommit",
        "lint",
        "pytest",
        "docs",
        "build",
    ]


def test_selected_steps_support_copy_only_and_subset_runs() -> None:
    assert validate_template.resolve_selected_steps(parse_args("--copy-only")) == ["copy"]
    assert validate_template.resolve_selected_steps(parse_args("--run", "lint", "--run", "pytest")) == [
        "copy",
        "install",
        "lint",
        "pytest",
    ]
    assert validate_template.resolve_selected_steps(parse_args("--run", "precommit")) == [
        "copy",
        "install",
        "precommit",
        "lint",
    ]


def test_repo_root_detection_points_to_repository_root() -> None:
    assert validate_template.REPO_ROOT == ROOT


def test_build_summary_lines_highlight_failed_step() -> None:
    report = {
        "success": False,
        "project_name": "Template Validation",
        "project_slug": "template-validation",
        "run_id": "run-id",
        "steps": [
            {
                "name": "copy",
                "status": "passed",
                "duration_seconds": 1.2,
                "returncode": 0,
            },
            {
                "name": "lint",
                "status": "failed",
                "duration_seconds": 2.3,
                "returncode": 1,
            },
        ],
        "failed_step": "lint",
        "failed_log_path": "/tmp/lint.log",
        "summary_path": "/tmp/summary.txt",
        "markdown_report_path": "/tmp/report.md",
        "json_report_path": "/tmp/report.json",
        "logs_root": "/tmp/logs",
    }

    lines = validate_template.build_summary_lines(report)

    assert lines[0] == "Overall result: FAIL"
    assert "- [PASS] copy (1.2s, exit=0)" in lines
    assert "- [FAIL] lint (2.3s, exit=1)" in lines
    assert "Failed step: lint" in lines
    assert "Failing log: /tmp/lint.log" in lines


def test_copy_step_uses_repository_root_without_recursive_manual_script(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    report_root = tmp_path / "report"
    ensure_workspace = validate_template.ensure_directory
    ensure_workspace(workspace_root)
    ensure_workspace(report_root)

    answers_file = report_root / "copier-answers.json"
    validate_template.write_data_file(answers_file, "Smoke Copy")
    commands = validate_template.build_commands(
        copier_command=validate_template.resolve_copier_command(),
        answers_file=answers_file,
        workspace_root=workspace_root,
        python_command=sys.executable,
        venv_path=workspace_root / "smoke-copy" / ".venv-template-validation",
        package_name="smoke_copy",
        pytest_target="tests/test_import.py",
    )
    log_path = report_root / "copy.log"

    result = validate_template.run_step("copy", commands["copy"], workspace_root, log_path)

    project_root = workspace_root / "smoke-copy"
    try:
        assert result.status == "passed"
        assert project_root.exists()
        assert (project_root / ".copier-answers.yml").exists()
        assert not (project_root / "tests" / "manual" / "validate_template.py").exists()
        log_text = log_path.read_text(encoding="utf-8")
        assert str(validate_template.REPO_ROOT) in log_text
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)
        shutil.rmtree(report_root, ignore_errors=True)


def test_build_commands_use_generated_makefile() -> None:
    commands = validate_template.build_commands(
        copier_command=["copier"],
        answers_file=Path("/tmp/answers.json"),
        workspace_root=Path("/tmp/workspace"),
        python_command="python3.12",
        venv_path=Path("/tmp/workspace/project/.venv-template-validation"),
        package_name="demo_pkg",
        pytest_target="tests/test_import.py",
    )

    assert commands["install"] == [["make", "install", "VENV=.venv-template-validation", "PYTHON=python3.12"]]
    assert commands["precommit"] == [[
        "make",
        "precommit",
        "VENV=.venv-template-validation",
        "PRE_COMMIT_SKIP=ruff,ruff-format,mypy",
    ]]
    assert commands["lint"] == [["make", "lint", "VENV=.venv-template-validation"]]
    assert commands["pytest"] == [["make", "test", "VENV=.venv-template-validation", "TEST_ARGS=tests/test_import.py -v"]]


def test_markdown_report_contains_more_detail_than_summary() -> None:
    report = {
        "success": True,
        "project_name": "Template Validation",
        "project_slug": "template-validation",
        "run_id": "run-id",
        "summary_path": "/tmp/summary.txt",
        "markdown_report_path": "/tmp/report.md",
        "json_report_path": "/tmp/report.json",
        "logs_root": "/tmp/logs",
        "workspace_root": "/tmp/workspace",
        "project_root": "/tmp/workspace/template-validation",
        "python_command": "python3.12",
        "python_version": "3.12",
        "copier_command": "copier",
        "selected_steps": ["copy", "install", "lint"],
        "pytest_target": "tests",
        "cleanup": {"performed": True, "kept": False},
        "failed_step": None,
        "failed_log_path": None,
        "steps": [
            {
                "name": "lint",
                "status": "passed",
                "duration_seconds": 1.0,
                "returncode": 0,
                "cwd": "/tmp/workspace/template-validation",
                "log_path": "/tmp/logs/lint.log",
                "commands": ["make lint VENV=.venv-template-validation"],
            }
        ],
    }

    summary_text = "\n".join(validate_template.build_summary_lines(report))
    markdown_text = validate_template.build_markdown_report(report)

    assert "## Step Details" in markdown_text
    assert "- Working directory: `/tmp/workspace/template-validation`" in markdown_text
    assert len(markdown_text) > len(summary_text)
