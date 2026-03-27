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

    @classmethod
    def spec(cls) -> dict:
        return {
            "type": cls.__name__,
            "category": cls.category,
            "display_name": cls.display_name,
            "description": cls.description,
            "params": cls.param_schema,
        }
