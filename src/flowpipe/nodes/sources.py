"""Source nodes - data ingestion from files and databases."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine, text

from flowpipe.nodes.base import BaseNode
from flowpipe.nodes.registry import register


@register
class CSVSource(BaseNode):
    category = "source"
    display_name = "CSV File"
    description = "Load data from a CSV file"
    param_schema = [
        {"name": "filename", "type": "file", "label": "CSV File", "required": True},
        {"name": "delimiter", "type": "text", "label": "Delimiter", "default": ","},
        {"name": "encoding", "type": "text", "label": "Encoding", "default": "utf-8"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        path = os.path.join(self.upload_dir, self.params["filename"])
        return pd.read_csv(
            path,
            delimiter=self.params.get("delimiter", ","),
            encoding=self.params.get("encoding", "utf-8"),
        )


@register
class ExcelSource(BaseNode):
    category = "source"
    display_name = "Excel File"
    description = "Load data from an Excel (.xlsx) file"
    param_schema = [
        {"name": "filename", "type": "file", "label": "Excel File", "required": True},
        {"name": "sheet_name", "type": "text", "label": "Sheet Name", "default": ""},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        path = os.path.join(self.upload_dir, self.params["filename"])
        sheet = self.params.get("sheet_name", "") or 0
        return pd.read_excel(path, sheet_name=sheet)


@register
class JSONSource(BaseNode):
    category = "source"
    display_name = "JSON File"
    description = "Load data from a JSON file"
    param_schema = [
        {"name": "filename", "type": "file", "label": "JSON File", "required": True},
        {"name": "orient", "type": "select", "label": "Orientation",
         "options": ["records", "columns", "index", "split"], "default": "records"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        path = os.path.join(self.upload_dir, self.params["filename"])
        return pd.read_json(path, orient=self.params.get("orient", "records"))


@register
class SQLSource(BaseNode):
    category = "source"
    display_name = "SQL Query"
    description = "Load data via SQL query from any SQLAlchemy-supported database"
    param_schema = [
        {"name": "connection_string", "type": "text", "label": "Connection String",
         "required": True, "placeholder": "sqlite:///data.db"},
        {"name": "query", "type": "textarea", "label": "SQL Query",
         "required": True, "placeholder": "SELECT * FROM table_name"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        engine = create_engine(self.params["connection_string"])
        with engine.connect() as conn:
            return pd.read_sql(text(self.params["query"]), conn)


@register
class SampleData(BaseNode):
    category = "source"
    display_name = "Sample Data"
    description = "Generate sample data for testing pipelines"
    param_schema = [
        {"name": "dataset", "type": "select", "label": "Dataset",
         "options": ["sales", "employees", "timeseries"], "default": "sales"},
        {"name": "rows", "type": "number", "label": "Number of Rows", "default": 100},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        import numpy as np

        n = int(self.params.get("rows", 100))
        rng = np.random.default_rng(42)
        dataset = self.params.get("dataset", "sales")

        if dataset == "sales":
            return pd.DataFrame({
                "date": pd.date_range("2024-01-01", periods=n, freq="D"),
                "product": rng.choice(["Widget A", "Widget B", "Gadget X", "Gadget Y"], n),
                "region": rng.choice(["North", "South", "East", "West"], n),
                "quantity": rng.integers(1, 50, n),
                "price": (rng.random(n) * 100).round(2),
            })
        elif dataset == "employees":
            return pd.DataFrame({
                "id": range(1, n + 1),
                "name": [f"Employee_{i}" for i in range(1, n + 1)],
                "department": rng.choice(["Engineering", "Sales", "Marketing", "HR"], n),
                "salary": (rng.normal(70000, 15000, n)).round(2),
                "hire_date": pd.date_range("2020-01-01", periods=n, freq="7D"),
            })
        else:
            return pd.DataFrame({
                "timestamp": pd.date_range("2024-01-01", periods=n, freq="h"),
                "value": np.cumsum(rng.normal(0, 1, n)).round(4),
                "category": rng.choice(["A", "B", "C"], n),
            })
