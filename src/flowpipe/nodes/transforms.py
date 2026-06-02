"""Transform nodes - data manipulation and enrichment."""

from __future__ import annotations

import pandas as pd

from flowpipe.nodes.base import BaseNode
from flowpipe.nodes.registry import register


@register
class FilterRows(BaseNode):
    category = "transform"
    display_name = "Filter Rows"
    description = "Keep rows matching a condition (pandas query syntax)"
    param_schema = [
        {"name": "condition", "type": "text", "label": "Condition",
         "required": True, "placeholder": "price > 50 and region == 'North'"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0].copy()
        return df.query(self.params["condition"])


@register
class SelectColumns(BaseNode):
    category = "transform"
    display_name = "Select Columns"
    description = "Keep only the specified columns"
    param_schema = [
        {"name": "columns", "type": "text", "label": "Columns (comma-separated)",
         "required": True, "placeholder": "name, date, price"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        cols = [c.strip() for c in self.params["columns"].split(",") if c.strip()]
        return inputs[0][cols].copy()


@register
class DropColumns(BaseNode):
    category = "transform"
    display_name = "Drop Columns"
    description = "Remove specified columns"
    param_schema = [
        {"name": "columns", "type": "text", "label": "Columns (comma-separated)",
         "required": True},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        cols = [c.strip() for c in self.params["columns"].split(",") if c.strip()]
        return inputs[0].drop(columns=cols)


@register
class RenameColumns(BaseNode):
    category = "transform"
    display_name = "Rename Columns"
    description = "Rename columns using old=new pairs"
    param_schema = [
        {"name": "mapping", "type": "textarea", "label": "Mapping (old=new, one per line)",
         "required": True, "placeholder": "old_name=new_name"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        mapping = {}
        for line in self.params["mapping"].strip().splitlines():
            if "=" in line:
                old, new = line.split("=", 1)
                mapping[old.strip()] = new.strip()
        return inputs[0].rename(columns=mapping)


@register
class SortRows(BaseNode):
    category = "transform"
    display_name = "Sort"
    description = "Sort by one or more columns"
    param_schema = [
        {"name": "columns", "type": "text", "label": "Sort Columns (comma-separated)",
         "required": True},
        {"name": "ascending", "type": "select", "label": "Order",
         "options": ["ascending", "descending"], "default": "ascending"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        cols = [c.strip() for c in self.params["columns"].split(",") if c.strip()]
        asc = self.params.get("ascending", "ascending") == "ascending"
        return inputs[0].sort_values(cols, ascending=asc)


@register
class GroupAggregate(BaseNode):
    category = "transform"
    display_name = "Group & Aggregate"
    description = "Group by columns and aggregate with sum/mean/count/min/max"
    param_schema = [
        {"name": "group_by", "type": "text", "label": "Group By (comma-separated)",
         "required": True, "placeholder": "region, product"},
        {"name": "aggregations", "type": "textarea",
         "label": "Aggregations (column=func, one per line)",
         "required": True, "placeholder": "price=sum\nquantity=mean"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        group_cols = [c.strip() for c in self.params["group_by"].split(",") if c.strip()]
        agg_map: dict[str, str] = {}
        for line in self.params["aggregations"].strip().splitlines():
            if "=" in line:
                col, func = line.split("=", 1)
                agg_map[col.strip()] = func.strip()
        return inputs[0].groupby(group_cols, as_index=False).agg(agg_map)


@register
class JoinTables(BaseNode):
    category = "transform"
    display_name = "Join"
    description = "Join two tables on key columns (connect two inputs)"
    param_schema = [
        {"name": "on", "type": "text", "label": "Join Key (comma-separated)", "required": True},
        {"name": "how", "type": "select", "label": "Join Type",
         "options": ["inner", "left", "right", "outer"], "default": "inner"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        if len(inputs) < 2:
            raise ValueError("Join requires exactly 2 inputs")
        keys = [c.strip() for c in self.params["on"].split(",") if c.strip()]
        return inputs[0].merge(inputs[1], on=keys, how=self.params.get("how", "inner"))


@register
class Deduplicate(BaseNode):
    category = "transform"
    display_name = "Deduplicate"
    description = "Remove duplicate rows"
    param_schema = [
        {"name": "subset", "type": "text", "label": "Columns (comma-separated, blank = all)",
         "default": ""},
        {"name": "keep", "type": "select", "label": "Keep",
         "options": ["first", "last"], "default": "first"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        subset_str = self.params.get("subset", "").strip()
        subset = [c.strip() for c in subset_str.split(",") if c.strip()] or None
        return inputs[0].drop_duplicates(subset=subset, keep=self.params.get("keep", "first"))


@register
class AddColumn(BaseNode):
    category = "transform"
    display_name = "Add Column"
    description = "Create a new column using a Python expression"
    param_schema = [
        {"name": "name", "type": "text", "label": "Column Name", "required": True},
        {"name": "expression", "type": "text", "label": "Expression (uses df[col])",
         "required": True, "placeholder": "df['price'] * df['quantity']"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0].copy()
        df[self.params["name"]] = eval(self.params["expression"], {"df": df, "pd": pd})  # noqa: S307
        return df


@register
class CastTypes(BaseNode):
    category = "transform"
    display_name = "Cast Types"
    description = "Convert column data types"
    param_schema = [
        {"name": "mapping", "type": "textarea", "label": "Column=Type (one per line)",
         "required": True, "placeholder": "price=float\ndate=datetime"},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0].copy()
        for line in self.params["mapping"].strip().splitlines():
            if "=" in line:
                col, dtype = line.split("=", 1)
                col, dtype = col.strip(), dtype.strip()
                if dtype == "datetime":
                    df[col] = pd.to_datetime(df[col])
                else:
                    df[col] = df[col].astype(dtype)
        return df


@register
class FillMissing(BaseNode):
    category = "transform"
    display_name = "Fill Missing"
    description = "Fill NaN/null values"
    param_schema = [
        {"name": "method", "type": "select", "label": "Method",
         "options": ["value", "ffill", "bfill", "mean", "median"], "default": "value"},
        {"name": "value", "type": "text",
         "label": "Fill Value (for 'value' method)", "default": "0"},
        {"name": "columns", "type": "text", "label": "Columns (blank = all)", "default": ""},
    ]

    def execute(self, inputs: list[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0].copy()
        method = self.params.get("method", "value")
        cols_str = self.params.get("columns", "").strip()
        cols = (
            [c.strip() for c in cols_str.split(",") if c.strip()]
            if cols_str else df.columns.tolist()
        )

        if method == "ffill":
            df[cols] = df[cols].ffill()
        elif method == "bfill":
            df[cols] = df[cols].bfill()
        elif method == "mean":
            for c in cols:
                if pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].mean())
        elif method == "median":
            for c in cols:
                if pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].median())
        else:
            fill_val = self.params.get("value", "0")
            try:
                fill_val = float(fill_val)
            except ValueError:
                pass
            df[cols] = df[cols].fillna(fill_val)
        return df
