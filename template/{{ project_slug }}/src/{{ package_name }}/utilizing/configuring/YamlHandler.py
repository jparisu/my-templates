from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeAlias, cast

import yaml

from ..names import naming_convention
from ..structuring.GenericEnumRegistry import GenericEnumRegistry
from ..structuring.GenericParameter import GenericParameter

YamlMappingTarget: TypeAlias = type[GenericEnumRegistry] | type[GenericParameter]


class YamlHandler:
    """
    Load, hold, combine, map, and dump YAML-backed configuration data.

    The handler supports three main workflows:

    1. Loading YAML data from a mapping or from a file on disk.
    2. Expanding YAML references such as ``yaml-file`` so several files behave
       like a single logical configuration.
    3. Converting selected YAML branches into Python objects backed by
       ``GenericEnumRegistry`` or ``GenericParameter`` implementations.
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        *,
        source_path: str | Path | None = None,
        concatenation_key: str = "yaml-file",
        mapping_targets: dict[str, YamlMappingTarget] | None = None,
    ) -> None:
        """
        Store the raw YAML payload and the rules used to process it.

        Args:
            data:
                Raw YAML content already loaded into a dictionary. The handler
                keeps this payload as the starting point for later
                concatenation and object-mapping passes.
            source_path:
                Optional file path pointing to the origin of ``data``. Relative
                file-resolution logic uses this location as the base for
                relative ``concatenation_key`` references.
            concatenation_key:
                YAML key that signals an extra file must be loaded and merged
                into the current configuration.
            mapping_targets:
                Mapping from YAML key names to Python classes. Each target class
                must implement either ``GenericEnumRegistry`` or
                ``GenericParameter`` so YAML values can be converted into typed
                Python objects.
        """
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise TypeError("YamlHandler expects the YAML root data to be a dictionary.")

        self._data = deepcopy(data)
        self._source_path = Path(source_path).expanduser().resolve() if source_path else None
        self.concatenation_key = str(concatenation_key)
        self._mapping_targets: dict[str, YamlMappingTarget] = {}

        for key, target in (mapping_targets or {}).items():
            self.register_mapping_target(key, target)

    @classmethod
    def from_file(
        cls,
        yaml_file: str | Path,
        *,
        concatenation_key: str = "yaml-file",
        mapping_targets: dict[str, YamlMappingTarget] | None = None,
    ) -> "YamlHandler":
        """
        Build a handler from a YAML file on disk.

        The file is parsed immediately so the handler is ready to resolve
        concatenated YAML files and typed object mappings.
        """
        normalized_path = Path(yaml_file).expanduser().resolve()
        data = cls._read_yaml_mapping(normalized_path)
        return cls(
            data=data,
            source_path=normalized_path,
            concatenation_key=concatenation_key,
            mapping_targets=mapping_targets,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        source_path: str | Path | None = None,
        concatenation_key: str = "yaml-file",
        mapping_targets: dict[str, YamlMappingTarget] | None = None,
    ) -> "YamlHandler":
        """
        Build a handler from an in-memory dictionary.

        This constructor is intended for tests and programmatic configuration
        generation where YAML has already been parsed elsewhere.
        """
        return cls(
            data=data,
            source_path=source_path,
            concatenation_key=concatenation_key,
            mapping_targets=mapping_targets,
        )

    def register_mapping_target(self, key: str, target: YamlMappingTarget) -> None:
        """
        Register or replace the class used to convert one YAML key.

        Args:
            key:
                YAML field name whose value should later be converted.
            target:
                Class implementing ``GenericEnumRegistry`` or
                ``GenericParameter``.
        """
        if not isinstance(target, type):
            raise TypeError("Mapping targets must be classes.")
        if not issubclass(target, (GenericEnumRegistry, GenericParameter)):
            raise TypeError(
                "Mapping targets must inherit from GenericEnumRegistry or GenericParameter."
            )

        self._mapping_targets[naming_convention(key)] = target

    def combine(self) -> dict[str, Any]:
        """
        Return the fully combined YAML dictionary.

        The handler recursively follows ``concatenation_key`` references and
        returns the merged dictionary that represents the complete
        configuration.
        """
        return self._combine_mapping_internal(
            base_data=deepcopy(self._data),
            source_path=self._source_path.parent if self._source_path else None,
            active_sources=frozenset({self._source_path}) if self._source_path else frozenset(),
        )

    def resolve_mapped_objects(self) -> dict[str, Any]:
        """
        Return a dictionary where configured YAML keys are replaced by objects.

        For each registered mapping key, YAML values are converted into:
        - enum members or enum-derived values for ``GenericEnumRegistry``.
        - dataclass-like parameter objects for ``GenericParameter``.
        """
        return cast(dict[str, Any], self._resolve_mapping_value(self.combine()))

    def to_dict(self, *, resolve_mapped_objects: bool = False) -> dict[str, Any]:
        """
        Export the handler state as a plain dictionary.

        Args:
            resolve_mapped_objects:
                When ``False``, the returned dictionary should reflect the
                combined YAML content. When ``True``, the returned dictionary
                should include converted Python objects for the registered keys.
        """
        if resolve_mapped_objects:
            return self.resolve_mapped_objects()
        return self.combine()

    def dump(
        self,
        yaml_file: str | Path,
        *,
        resolve_mapped_objects: bool = False,
    ) -> Path:
        """
        Write the processed configuration back to disk.

        Args:
            yaml_file:
                Destination path where the processed configuration should be
                written.
            resolve_mapped_objects:
                Controls whether the dumped content should come from the pure
                combined YAML representation or from the object-mapped view.

        Returns:
            The normalized destination path used for the dump operation.
        """
        destination = Path(yaml_file).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        payload = self.to_dict(resolve_mapped_objects=resolve_mapped_objects)
        serializable_payload = self._serialize_for_yaml(payload)
        destination.write_text(
            yaml.safe_dump(serializable_payload, sort_keys=False),
            encoding="utf-8",
        )
        return destination

    def _load_yaml_file(self, yaml_file: str | Path) -> dict[str, Any]:
        """
        Read one YAML file and return its parsed dictionary representation.

        This helper exists so file I/O and YAML parsing stay isolated from the
        higher-level combination logic.
        """
        candidate = Path(yaml_file).expanduser()
        if not candidate.is_absolute():
            if self._source_path is None:
                candidate = (Path.cwd() / candidate).resolve()
            else:
                candidate = (self._source_path.parent / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return self._read_yaml_mapping(candidate)

    def _combine_mapping(
        self,
        base_data: dict[str, Any],
        *,
        source_path: Path | None,
    ) -> dict[str, Any]:
        """
        Expand one mapping by resolving any nested YAML concatenation keys.

        Args:
            base_data:
                Mapping currently being processed.
            source_path:
                Directory context used to resolve relative file references found
                inside ``base_data``.
        """
        return self._combine_mapping_internal(
            base_data=base_data,
            source_path=source_path,
            active_sources=frozenset(),
        )

    def _merge_dicts(self, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        """
        Merge two dictionaries into one combined configuration payload.

        The right-hand mapping takes precedence for overlapping keys. When both
        values are dictionaries, the merge is recursive.
        """
        merged = deepcopy(left)
        for key, right_value in right.items():
            left_value = merged.get(key)
            if isinstance(left_value, dict) and isinstance(right_value, dict):
                merged[key] = self._merge_dicts(left_value, right_value)
                continue
            merged[key] = deepcopy(right_value)
        return merged

    def _resolve_single_mapping(self, key: str, value: Any) -> Any:
        """
        Convert one YAML value according to the registered class for ``key``.

        This helper should centralize the conversion rules for
        ``GenericEnumRegistry`` and ``GenericParameter`` targets.
        """
        target = self._mapping_targets[naming_convention(key)]

        if issubclass(target, GenericParameter):
            if isinstance(value, target):
                return value
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"Key '{key}' must contain a mapping to build {target.__name__}."
                )
            return target.from_dict(value)

        if isinstance(value, target):
            return value
        if isinstance(value, GenericEnumRegistry):
            value = value.value
        return target.find(str(value))

    @staticmethod
    def _read_yaml_mapping(yaml_file: Path) -> dict[str, Any]:
        """Load a YAML file and ensure its root element is a dictionary."""
        loaded = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise TypeError(f"YAML root in {yaml_file} must be a dictionary.")
        return cast(dict[str, Any], loaded)

    def _combine_mapping_internal(
        self,
        base_data: dict[str, Any],
        *,
        source_path: Path | None,
        active_sources: frozenset[Path],
    ) -> dict[str, Any]:
        """Recursively expand include references while tracking visited files."""
        merged_includes: dict[str, Any] = {}
        include_value = base_data.get(self.concatenation_key)
        if include_value is not None:
            for include_path in self._resolve_include_paths(include_value, source_path):
                if include_path in active_sources:
                    raise ValueError(f"Cyclic YAML include detected for {include_path}.")
                included_data = self._load_yaml_file(include_path)
                included_mapping = self._combine_mapping_internal(
                    base_data=included_data,
                    source_path=include_path.parent,
                    active_sources=active_sources.union({include_path}),
                )
                merged_includes = self._merge_dicts(merged_includes, included_mapping)

        local_mapping: dict[str, Any] = {}
        for key, value in base_data.items():
            if key == self.concatenation_key:
                continue
            local_mapping[key] = self._combine_value(value, source_path, active_sources)

        return self._merge_dicts(merged_includes, local_mapping)

    def _combine_value(
        self,
        value: Any,
        source_path: Path | None,
        active_sources: frozenset[Path],
    ) -> Any:
        """Apply nested include expansion to mappings and lists."""
        if isinstance(value, dict):
            return self._combine_mapping_internal(
                base_data=cast(dict[str, Any], value),
                source_path=source_path,
                active_sources=active_sources,
            )
        if isinstance(value, list):
            return [self._combine_value(item, source_path, active_sources) for item in value]
        return deepcopy(value)

    def _resolve_include_paths(
        self,
        include_value: Any,
        source_path: Path | None,
    ) -> list[Path]:
        """Normalize include declarations to absolute filesystem paths."""
        if isinstance(include_value, (str, Path)):
            raw_paths: Sequence[str | Path] = [include_value]
        elif isinstance(include_value, Sequence) and not isinstance(include_value, (str, bytes)):
            raw_paths = cast(Sequence[str | Path], include_value)
        else:
            raise TypeError(
                f"'{self.concatenation_key}' must be a path or a sequence of paths."
            )

        resolved_paths: list[Path] = []
        for raw_path in raw_paths:
            if not isinstance(raw_path, (str, Path)):
                raise TypeError(
                    f"'{self.concatenation_key}' entries must be strings or Path objects."
                )
            candidate = Path(raw_path).expanduser()
            if not candidate.is_absolute():
                if source_path is None:
                    raise ValueError(
                        "Relative YAML includes require the handler to know the source path."
                    )
                candidate = source_path / candidate
            resolved_paths.append(candidate.resolve())
        return resolved_paths

    def _resolve_mapping_value(self, value: Any) -> Any:
        """Walk a YAML-like structure and replace registered keys with objects."""
        if isinstance(value, dict):
            resolved: dict[str, Any] = {}
            for key, raw_value in value.items():
                processed_value = self._resolve_mapping_value(raw_value)
                if naming_convention(str(key)) in self._mapping_targets:
                    processed_value = self._resolve_single_mapping(str(key), processed_value)
                resolved[key] = processed_value
            return resolved
        if isinstance(value, list):
            return [self._resolve_mapping_value(item) for item in value]
        return value

    def _serialize_for_yaml(self, value: Any) -> Any:
        """Convert handler output into a structure supported by YAML dumping."""
        if isinstance(value, GenericParameter):
            return self._serialize_for_yaml(value.to_dict())
        if isinstance(value, GenericEnumRegistry):
            return self._serialize_for_yaml(value.value)
        if isinstance(value, dict):
            return {key: self._serialize_for_yaml(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._serialize_for_yaml(item) for item in value]
        if isinstance(value, tuple):
            return [self._serialize_for_yaml(item) for item in value]
        return deepcopy(value)
