from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_copier_config_documents_core_settings() -> None:
    content = read("copier.yml")

    assert "_subdirectory: template" in content
    assert "_answers_file: .copier-answers.yml" in content
    assert "_templates_suffix: .jinja" in content
    assert 'min_copier_version: "9.0.0"' in content
    assert "_tasks:" in content
    assert "message_before_copy" in content
    assert "message_before_update" in content


def test_answers_template_records_update_metadata() -> None:
    content = read("{{ _copier_conf.answers_file }}.jinja")

    assert "_src_path:" in content
    assert "_commit:" in content
    assert "project_name: {{ project_name | to_json }}" in content
    assert "include_cli: {{ include_cli | to_json }}" in content


def test_readme_documents_copy_and_update_commands() -> None:
    content = read("README.md")

    assert "## Copy A Project" in content
    assert "## Update A Generated Project" in content
    assert "copier copy" in content
    assert "copier update" in content
    assert "--trust" in content
    assert ".copier-answers.yml" in content
