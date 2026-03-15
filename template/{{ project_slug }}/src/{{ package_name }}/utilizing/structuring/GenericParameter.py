from __future__ import annotations

import logging
import types
from collections.abc import Mapping
from dataclasses import MISSING, asdict, fields, is_dataclass
from typing import Any, TypeVar, Union, cast, get_args, get_origin, get_type_hints

from ..names import naming_convention
from .GenericEnumRegistry import GenericEnumRegistry

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="GenericParameter")


class GenericParameter:
    @classmethod
    def from_dict(cls: type[T], data: Mapping[str, Any]) -> T:
        """Create a dataclass instance from dictionary values and aliases."""
        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a dataclass to use GenericParameter.")

        field_map = cls._field_type_map()
        normalized = cls._normalize_input_mapping(data, field_map, owner_name=cls.__name__)
        init_kwargs: dict[str, Any] = {}
        post_init_updates: dict[str, Any] = {}

        for field in fields(cls):
            if field.name in normalized:
                converted = cls._convert_value(field_map[field.name], normalized[field.name])
                if field.init:
                    init_kwargs[field.name] = converted
                else:
                    post_init_updates[field.name] = converted
                continue
            if not field.init:
                continue
            if field.default is not MISSING or field.default_factory is not MISSING:
                continue
            raise TypeError(f"Missing required field '{field.name}' for {cls.__name__}.")

        instance = cls(**init_kwargs)
        for field_name, value in post_init_updates.items():
            setattr(instance, field_name, value)
        return instance

    def update_from_dict(self: T, data: Mapping[str, Any]) -> T:
        """Update dataclass fields from key/value input, applying alias resolution."""
        if not is_dataclass(self):
            raise TypeError(f"{type(self).__name__} must be a dataclass to use GenericParameter.")
        field_map = type(self)._field_type_map()
        normalized = type(self)._normalize_input_mapping(
            data,
            field_map,
            owner_name=type(self).__name__,
        )

        for target_key, value in normalized.items():
            target_type = field_map[target_key]
            setattr(self, target_key, self._convert_value(target_type, value))
        return self

    @classmethod
    def _field_type_map(cls) -> dict[str, Any]:
        try:
            type_hints = get_type_hints(cls)
        except Exception:  # pragma: no cover - defensive fallback for unresolved annotations
            type_hints = {}
        return {
            field.name: type_hints.get(field.name, field.type) for field in fields(cast(Any, cls))
        }

    @classmethod
    def _normalize_input_mapping(
        cls,
        data: Mapping[str, Any],
        field_map: Mapping[str, Any],
        *,
        owner_name: str,
    ) -> dict[str, Any]:
        aliases = cls.aliases()
        normalized_aliases = {naming_convention(alias): target for alias, target in aliases.items()}
        normalized_fields = {naming_convention(field_name): field_name for field_name in field_map}
        normalized: dict[str, Any] = {}

        for key, value in data.items():
            normalized_key = naming_convention(str(key))
            target_key = aliases.get(str(key))
            if target_key is None:
                target_key = normalized_aliases.get(normalized_key)
            if target_key is None:
                target_key = str(key) if str(key) in field_map else None
            if target_key is None:
                target_key = normalized_fields.get(normalized_key)

            if target_key is None:
                logger.warning("Key '%s' not recognized in %s", key, owner_name)
                continue
            if target_key not in field_map:
                target_key = normalized_fields.get(naming_convention(target_key))
            if target_key is None:
                logger.warning("Alias '%s' targets an unknown field in %s", key, owner_name)
                continue
            normalized[target_key] = value
        return normalized

    @staticmethod
    def _convert_value(target_type: Any, value: Any) -> Any:
        if value is None:
            return None

        # Handle Optional/Union types
        origin = get_origin(target_type)
        if origin in (Union, types.UnionType):
            args = get_args(target_type)
            potential_types = [a for a in args if a is not type(None)]
            target_type = potential_types[0] if potential_types else target_type

        # Auto-convert Registry Enums
        if isinstance(target_type, type) and issubclass(target_type, GenericEnumRegistry):
            if isinstance(value, target_type):
                return value
            if isinstance(value, GenericEnumRegistry):
                value = value.value
            return target_type.find(value)

        # Support generic classes exposing ``from_value`` / ``from_string``.
        if isinstance(target_type, type):
            if isinstance(value, target_type):
                return value

            from_value = getattr(target_type, "from_value", None)
            if callable(from_value):
                return from_value(value)

            if isinstance(value, str):
                from_string = getattr(target_type, "from_string", None)
                if callable(from_string):
                    return from_string(value)

        return value

    def to_dict(self, target_format: str | None = None) -> dict[str, Any]:
        """
        Converts the dataclass to a dict.
        If ``target_format`` is provided, values exposing ``to_<target_format>``
        are serialized through that method.
        """
        if not is_dataclass(self):
            raise TypeError(f"{type(self).__name__} must be a dataclass to use GenericParameter.")
        raw = asdict(cast(Any, self))
        if not target_format:
            return raw

        processed = {}
        for key, value in raw.items():
            # If the field exposes a target serializer, use it.
            actual_member = getattr(self, key)
            method_name = f"to_{target_format}"
            serializer = getattr(actual_member, method_name, None)
            if callable(serializer):
                processed[key] = serializer()
                continue
            processed[key] = value
        return processed

    def set_default_value(self, field_name: str, default_value: Any) -> None:
        """Set a value if the current field value is ``None``."""
        if getattr(self, field_name) is None:
            setattr(self, field_name, default_value)

    @classmethod
    def aliases(cls) -> dict[str, str]:
        """Return a map from input aliases to target field names."""
        return {}

    def copy(self: T) -> T:
        """Return a copy of this parameter instance."""
        return self.__class__.from_dict(self.to_dict())
