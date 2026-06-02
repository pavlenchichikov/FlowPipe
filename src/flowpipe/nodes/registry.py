"""Global node registry - all node subclasses auto-register here."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flowpipe.nodes.base import BaseNode

_REGISTRY: dict[str, type[BaseNode]] = {}


def register(cls: type[BaseNode]) -> type[BaseNode]:
    _REGISTRY[cls.__name__] = cls
    return cls


def get_node_class(name: str) -> type[BaseNode] | None:
    return _REGISTRY.get(name)


def all_node_specs() -> list[dict]:
    return [cls.spec() for cls in _REGISTRY.values()]
