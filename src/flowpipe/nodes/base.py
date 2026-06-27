"""Base class for all pipeline nodes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseNode(ABC):
    """Every node receives params (from the UI) and executes on input DataFrames."""

    category: str = "misc"
    display_name: str = "Node"
    description: str = ""
    param_schema: list[dict] = []

    def __init__(self, params: dict[str, Any], upload_dir: str = "uploads"):
        self.params = params
        self.upload_dir = upload_dir

    @abstractmethod
    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        ...

    def codegen(self, input_vars: list) -> str:
        raise NotImplementedError(
            "%s does not implement codegen" % type(self).__name__
        )

    def output_columns(self, input_schemas: list) -> list | None:
        return input_schemas[0] if input_schemas else None

    @classmethod
    def allowed_options(cls, param_name: str) -> list | None:
        """Return the declared "options" list for a select param, or None if
        the param isn't a select / isn't found."""
        for field in cls.param_schema:
            if field.get("name") == param_name:
                return field.get("options")
        return None

    @classmethod
    def spec(cls) -> dict:
        return {
            "type": cls.__name__,
            "category": cls.category,
            "display_name": cls.display_name,
            "description": cls.description,
            "params": cls.param_schema,
        }
