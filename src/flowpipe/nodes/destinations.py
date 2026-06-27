"""Destination nodes - data export to files and databases."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine

from flowpipe.nodes.base import BaseNode
from flowpipe.nodes.registry import register


@register
class CSVDestination(BaseNode):
    category = "destination"
    display_name = "Export CSV"
    description = "Save data to a CSV file"
    param_schema = [
        {"name": "filename", "type": "text", "label": "Output Filename",
         "required": True, "placeholder": "output.csv"},
        {"name": "delimiter", "type": "text", "label": "Delimiter", "default": ","},
        {"name": "index", "type": "select", "label": "Include Index",
         "options": ["no", "yes"], "default": "no"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0]
        path = os.path.join(self.upload_dir, self.params["filename"])
        df.to_csv(
            path,
            sep=self.params.get("delimiter", ","),
            index=self.params.get("index", "no") == "yes",
        )
        return df

    def codegen(self, input_vars):
        return "%s.to_csv(%r, sep=%r, index=%s)" % (
            input_vars[0], self.params["filename"], self.params.get("delimiter", ","),
            self.params.get("index", "no") == "yes")

    def output_columns(self, input_schemas):
        return input_schemas[0] if input_schemas else None


@register
class ExcelDestination(BaseNode):
    category = "destination"
    display_name = "Export Excel"
    description = "Save data to an Excel (.xlsx) file"
    param_schema = [
        {"name": "filename", "type": "text", "label": "Output Filename",
         "required": True, "placeholder": "output.xlsx"},
        {"name": "sheet_name", "type": "text", "label": "Sheet Name", "default": "Sheet1"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0]
        path = os.path.join(self.upload_dir, self.params["filename"])
        df.to_excel(path, sheet_name=self.params.get("sheet_name", "Sheet1"), index=False)
        return df

    def codegen(self, input_vars):
        return "%s.to_excel(%r, sheet_name=%r, index=False)" % (
            input_vars[0], self.params["filename"], self.params.get("sheet_name", "Sheet1"))

    def output_columns(self, input_schemas):
        return input_schemas[0] if input_schemas else None


@register
class JSONDestination(BaseNode):
    category = "destination"
    display_name = "Export JSON"
    description = "Save data to a JSON file"
    param_schema = [
        {"name": "filename", "type": "text", "label": "Output Filename",
         "required": True, "placeholder": "output.json"},
        {"name": "orient", "type": "select", "label": "Orientation",
         "options": ["records", "columns", "index", "split"], "default": "records"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0]
        path = os.path.join(self.upload_dir, self.params["filename"])
        df.to_json(path, orient=self.params.get("orient", "records"), indent=2, force_ascii=False)
        return df

    def codegen(self, input_vars):
        return "%s.to_json(%r, orient=%r, indent=2, force_ascii=False)" % (
            input_vars[0], self.params["filename"], self.params.get("orient", "records"))

    def output_columns(self, input_schemas):
        return input_schemas[0] if input_schemas else None


@register
class SQLDestination(BaseNode):
    category = "destination"
    display_name = "Export to SQL"
    description = "Write data to a SQL database table"
    param_schema = [
        {"name": "connection_string", "type": "text", "label": "Connection String",
         "required": True, "placeholder": "sqlite:///output.db"},
        {"name": "table_name", "type": "text", "label": "Table Name", "required": True},
        {"name": "if_exists", "type": "select", "label": "If Table Exists",
         "options": ["replace", "append", "fail"], "default": "replace"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0]
        engine = create_engine(self.params["connection_string"])
        df.to_sql(
            self.params["table_name"],
            engine,
            if_exists=self.params.get("if_exists", "replace"),
            index=False,
        )
        return df

    def codegen(self, input_vars):
        return "%s.to_sql(%r, create_engine(%r), if_exists=%r, index=False)" % (
            input_vars[0], self.params["table_name"], self.params["connection_string"],
            self.params.get("if_exists", "replace"))

    def output_columns(self, input_schemas):
        return input_schemas[0] if input_schemas else None
