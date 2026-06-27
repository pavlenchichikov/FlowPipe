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

    def codegen(self, input_vars):
        p = self.params
        return "pd.read_csv(%r, delimiter=%r, encoding=%r)" % (
            p["filename"], p.get("delimiter", ","), p.get("encoding", "utf-8"))

    def output_columns(self, input_schemas):
        return None


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

    def codegen(self, input_vars):
        sheet = self.params.get("sheet_name", "") or 0
        return "pd.read_excel(%r, sheet_name=%r)" % (self.params["filename"], sheet)

    def output_columns(self, input_schemas):
        return None


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

    def codegen(self, input_vars):
        return "pd.read_json(%r, orient=%r)" % (
            self.params["filename"], self.params.get("orient", "records"))

    def output_columns(self, input_schemas):
        return None


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

    def codegen(self, input_vars):
        return "pd.read_sql(text(%r), create_engine(%r).connect())" % (
            self.params["query"], self.params["connection_string"])

    def output_columns(self, input_schemas):
        return None


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

    def codegen(self, input_vars):
        n = int(self.params.get("rows", 100))
        ds = self.params.get("dataset", "sales")
        rng_expr = "np.random.default_rng(42)"
        if ds == "sales":
            return (
                "pd.DataFrame({"
                "'date': pd.date_range('2024-01-01', periods=%d, freq='D'), "
                "'product': %s.choice(['Widget A', 'Widget B', 'Gadget X', 'Gadget Y'], %d), "
                "'region': %s.choice(['North', 'South', 'East', 'West'], %d), "
                "'quantity': %s.integers(1, 50, %d), "
                "'price': (%s.random(%d) * 100).round(2)})"
                % (n, rng_expr, n, rng_expr, n, rng_expr, n, rng_expr, n)
            )
        elif ds == "employees":
            return (
                "pd.DataFrame({"
                "'id': range(1, %d + 1), "
                "'name': ['Employee_%%d' %% i for i in range(1, %d + 1)], "
                "'department': %s.choice(['Engineering', 'Sales', 'Marketing', 'HR'], %d), "
                "'salary': (%s.normal(70000, 15000, %d)).round(2), "
                "'hire_date': pd.date_range('2020-01-01', periods=%d, freq='7D')})"
                % (n, n, rng_expr, n, rng_expr, n, n)
            )
        else:
            return (
                "pd.DataFrame({"
                "'timestamp': pd.date_range('2024-01-01', periods=%d, freq='h'), "
                "'value': np.cumsum(%s.normal(0, 1, %d)).round(4), "
                "'category': %s.choice(['A', 'B', 'C'], %d)})"
                % (n, rng_expr, n, rng_expr, n)
            )

    def output_columns(self, input_schemas):
        cols = {
            "sales": ["date", "product", "region", "quantity", "price"],
            "employees": ["id", "name", "department", "salary", "hire_date"],
            "timeseries": ["timestamp", "value", "category"],
        }
        return cols.get(self.params.get("dataset", "sales"))
