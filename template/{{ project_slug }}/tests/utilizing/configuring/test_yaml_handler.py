from dataclasses import dataclass

import yaml

from {{ package_name }}.utilizing.configuring.YamlHandler import YamlHandler
from {{ package_name }}.utilizing.structuring.GenericEnumRegistry import GenericEnumRegistry
from {{ package_name }}.utilizing.structuring.GenericParameter import GenericParameter


class ExecutionMode(GenericEnumRegistry):
    FAST = "fast"
    SAFE = "safe"

    @classmethod
    def aliases(cls) -> dict[str, str]:
        return {"f": "FAST"}


@dataclass
class EngineParameters(GenericParameter):
    mode: ExecutionMode = ExecutionMode.SAFE
    retries: int = 1

    @classmethod
    def aliases(cls) -> dict[str, str]:
        return {"attempt-count": "retries"}


def test_combine_merges_included_yaml_and_local_overrides(tmp_path) -> None:
    defaults_file = tmp_path / "defaults.yml"
    defaults_file.write_text(
        "\n".join(
            [
                "mode: safe",
                "nested:",
                "  enabled: true",
                "  values:",
                "    left: 1",
                "items:",
                "  - 1",
                "  - 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    main_file = tmp_path / "main.yml"
    main_file.write_text(
        "\n".join(
            [
                "yaml-file: defaults.yml",
                "mode: fast",
                "nested:",
                "  values:",
                "    right: 2",
                "items:",
                "  - 3",
                "",
            ]
        ),
        encoding="utf-8",
    )

    handler = YamlHandler.from_file(main_file)

    assert handler.combine() == {
        "mode": "fast",
        "nested": {
            "enabled": True,
            "values": {"left": 1, "right": 2},
        },
        "items": [3],
    }


def test_resolve_mapped_objects_converts_registered_keys_recursively() -> None:
    handler = YamlHandler.from_dict(
        data={
            "mode": "f",
            "pipeline": {
                "params": {
                    "mode": "safe",
                    "attempt-count": 4,
                }
            },
        },
        mapping_targets={
            "mode": ExecutionMode,
            "params": EngineParameters,
        },
    )

    resolved = handler.resolve_mapped_objects()

    assert resolved["mode"] is ExecutionMode.FAST
    assert isinstance(resolved["pipeline"]["params"], EngineParameters)
    assert resolved["pipeline"]["params"].mode is ExecutionMode.SAFE
    assert resolved["pipeline"]["params"].retries == 4


def test_dump_reads_processes_and_writes_expected_yaml(tmp_path) -> None:
    defaults_file = tmp_path / "defaults.yml"
    defaults_file.write_text(
        "\n".join(
            [
                "service:",
                "  name: demo",
                "profile:",
                "  mode: safe",
                "  attempt-count: 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    main_file = tmp_path / "config.yml"
    main_file.write_text(
        "\n".join(
            [
                "yaml-file: defaults.yml",
                "profile:",
                "  mode: f",
                "",
            ]
        ),
        encoding="utf-8",
    )

    handler = YamlHandler.from_file(
        main_file,
        mapping_targets={"profile": EngineParameters},
    )

    output_file = tmp_path / "output.yml"
    dumped_path = handler.dump(output_file, resolve_mapped_objects=True)

    assert dumped_path == output_file.resolve()
    assert yaml.safe_load(output_file.read_text(encoding="utf-8")) == {
        "service": {"name": "demo"},
        "profile": {"mode": "fast", "retries": 2},
    }
