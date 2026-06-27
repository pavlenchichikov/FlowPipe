"""Transform nodes - data manipulation and enrichment."""

from __future__ import annotations

import pandas as pd

from flowpipe.nodes.base import BaseNode
from flowpipe.nodes.registry import register


def _cols(s: str) -> list:
    return [c.strip() for c in (s or "").split(",") if c.strip()]


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

    def codegen(self, input_vars: list) -> str:
        return "%s.query(%r)" % (input_vars[0], self.params["condition"])

    def output_columns(self, input_schemas: list) -> list | None:
        return input_schemas[0] if input_schemas else None


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

    def codegen(self, input_vars: list) -> str:
        return "%s[%r]" % (input_vars[0], _cols(self.params["columns"]))

    def output_columns(self, input_schemas: list) -> list | None:
        return _cols(self.params["columns"])


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

    def codegen(self, input_vars: list) -> str:
        return "%s.drop(columns=%r)" % (input_vars[0], _cols(self.params["columns"]))

    def output_columns(self, input_schemas: list) -> list | None:
        if not input_schemas:
            return None
        drop = set(_cols(self.params["columns"]))
        return [c for c in input_schemas[0] if c not in drop]


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
        return inputs[0].rename(columns=self._mapping())

    def _mapping(self) -> dict:
        m = {}
        for line in self.params["mapping"].strip().splitlines():
            if "=" in line:
                old, new = line.split("=", 1)
                m[old.strip()] = new.strip()
        return m

    def codegen(self, input_vars: list) -> str:
        return "%s.rename(columns=%r)" % (input_vars[0], self._mapping())

    def output_columns(self, input_schemas: list) -> list | None:
        if not input_schemas:
            return None
        m = self._mapping()
        return [m.get(c, c) for c in input_schemas[0]]


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

    def codegen(self, input_vars: list) -> str:
        asc = self.params.get("ascending", "ascending") == "ascending"
        return "%s.sort_values(%r, ascending=%s)" % (
            input_vars[0], _cols(self.params["columns"]), asc)

    def output_columns(self, input_schemas: list) -> list | None:
        return input_schemas[0] if input_schemas else None


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
        group_cols = _cols(self.params["group_by"])
        return inputs[0].groupby(group_cols, as_index=False).agg(self._aggmap())

    def _aggmap(self) -> dict:
        m = {}
        for line in self.params["aggregations"].strip().splitlines():
            if "=" in line:
                col, func = line.split("=", 1)
                m[col.strip()] = func.strip()
        return m

    def codegen(self, input_vars: list) -> str:
        return "%s.groupby(%r, as_index=False).agg(%r)" % (
            input_vars[0], _cols(self.params["group_by"]), self._aggmap())

    def output_columns(self, input_schemas: list) -> list | None:
        return _cols(self.params["group_by"]) + list(self._aggmap().keys())


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

    def codegen(self, input_vars: list) -> str:
        a = input_vars[0] if input_vars else "df"
        b = input_vars[1] if len(input_vars) > 1 else "df"
        return "%s.merge(%s, on=%r, how=%r)" % (
            a, b, _cols(self.params["on"]), self.params.get("how", "inner"))

    def output_columns(self, input_schemas: list) -> list | None:
        if len(input_schemas) < 2:
            return None
        on = set(_cols(self.params["on"]))
        right_extra = [c for c in input_schemas[1] if c not in on]
        return input_schemas[0] + right_extra


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

    def codegen(self, input_vars: list) -> str:
        subset = _cols(self.params.get("subset", "")) or None
        return "%s.drop_duplicates(subset=%r, keep=%r)" % (
            input_vars[0], subset, self.params.get("keep", "first"))

    def output_columns(self, input_schemas: list) -> list | None:
        return input_schemas[0] if input_schemas else None


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
        from flowpipe.safe_eval import safe_eval
        df = inputs[0].copy()
        df[self.params["name"]] = safe_eval(self.params["expression"], df)
        return df

    def codegen(self, input_vars: list) -> str:
        return "%s.assign(%s=lambda df: df.eval(%r))" % (
            input_vars[0], self.params["name"], self.params["expression"])

    def output_columns(self, input_schemas: list) -> list | None:
        if not input_schemas:
            return None
        return input_schemas[0] + [self.params["name"]]


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

    def codegen(self, input_vars: list) -> str:
        v = input_vars[0]
        kwargs = []
        for line in self.params["mapping"].strip().splitlines():
            if "=" in line:
                col, dtype = (x.strip() for x in line.split("=", 1))
                if dtype == "datetime":
                    kwargs.append("%s=pd.to_datetime(%s[%r])" % (col, v, col))
                else:
                    kwargs.append("%s=%s[%r].astype(%r)" % (col, v, col, dtype))
        if not kwargs:
            return v
        return "%s.assign(%s)" % (v, ", ".join(kwargs))

    def output_columns(self, input_schemas: list) -> list | None:
        return input_schemas[0] if input_schemas else None


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

    def codegen(self, input_vars: list) -> str:
        v = input_vars[0]
        method = self.params.get("method", "value")
        if method == "ffill":
            return "%s.ffill()" % v
        if method == "bfill":
            return "%s.bfill()" % v
        if method in ("mean", "median"):
            return "%s.fillna(%s.%s(numeric_only=True))" % (v, v, method)
        val = self.params.get("value", "0")
        try:
            val = float(val)
        except ValueError:
            pass
        return "%s.fillna(%r)" % (v, val)

    def output_columns(self, input_schemas: list) -> list | None:
        return input_schemas[0] if input_schemas else None


@register
class Union(BaseNode):
    category = "transform"
    display_name = "Union (Stack)"
    description = "Stack two or more tables vertically (append rows)"
    param_schema = []

    def execute(self, inputs):
        return pd.concat(inputs, ignore_index=True)

    def codegen(self, input_vars):
        return "pd.concat([%s], ignore_index=True)" % ", ".join(input_vars)

    def output_columns(self, input_schemas):
        seen = []
        for s in input_schemas:
            for c in (s or []):
                if c not in seen:
                    seen.append(c)
        return seen or None


@register
class Pivot(BaseNode):
    category = "transform"
    display_name = "Pivot"
    description = "Pivot long data to wide (index, columns, values)"
    param_schema = [
        {"name": "index", "type": "text", "label": "Index column(s)", "required": True},
        {"name": "columns", "type": "text", "label": "Columns from", "required": True},
        {"name": "values", "type": "text", "label": "Values", "required": True},
        {"name": "aggfunc", "type": "select", "label": "Aggregate",
         "options": ["sum", "mean", "count", "min", "max"], "default": "sum"},
    ]

    def execute(self, inputs):
        p = self.params
        idx = _cols(p["index"])
        out = inputs[0].pivot_table(index=idx, columns=p["columns"].strip(),
                                    values=p["values"].strip(),
                                    aggfunc=p.get("aggfunc", "sum"))
        return out.reset_index()

    def codegen(self, input_vars):
        p = self.params
        return ("%s.pivot_table(index=%r, columns=%r, values=%r, aggfunc=%r).reset_index()"
                % (input_vars[0], _cols(p["index"]), p["columns"].strip(),
                   p["values"].strip(), p.get("aggfunc", "sum")))

    def output_columns(self, input_schemas):
        return None  # pivot column names are data-dependent


@register
class Unpivot(BaseNode):
    category = "transform"
    display_name = "Unpivot (Melt)"
    description = "Melt wide data to long (id columns + value columns)"
    param_schema = [
        {"name": "id_vars", "type": "text", "label": "ID columns", "required": True},
        {"name": "value_vars", "type": "text", "label": "Value columns (blank = rest)", "default": ""},
        {"name": "var_name", "type": "text", "label": "Variable column name", "default": "variable"},
        {"name": "value_name", "type": "text", "label": "Value column name", "default": "value"},
    ]

    def execute(self, inputs):
        p = self.params
        value_vars = _cols(p.get("value_vars", "")) or None
        return inputs[0].melt(id_vars=_cols(p["id_vars"]), value_vars=value_vars,
                              var_name=p.get("var_name", "variable"),
                              value_name=p.get("value_name", "value"))

    def codegen(self, input_vars):
        p = self.params
        return ("%s.melt(id_vars=%r, value_vars=%r, var_name=%r, value_name=%r)"
                % (input_vars[0], _cols(p["id_vars"]), _cols(p.get("value_vars", "")) or None,
                   p.get("var_name", "variable"), p.get("value_name", "value")))

    def output_columns(self, input_schemas):
        p = self.params
        return _cols(p["id_vars"]) + [p.get("var_name", "variable"), p.get("value_name", "value")]


@register
class StringOp(BaseNode):
    category = "transform"
    display_name = "String Operation"
    description = "Apply a string operation to a text column"
    param_schema = [
        {"name": "column", "type": "text", "label": "Column", "required": True},
        {"name": "op", "type": "select", "label": "Operation",
         "options": ["upper", "lower", "strip", "title", "replace"], "default": "upper"},
        {"name": "find", "type": "text", "label": "Find (for replace)", "default": ""},
        {"name": "replace", "type": "text", "label": "Replace with", "default": ""},
    ]

    def execute(self, inputs):
        df = inputs[0].copy()
        col, op = self.params["column"].strip(), self.params.get("op", "upper")
        if op not in self.allowed_options("op"):
            raise ValueError("invalid op: %s" % op)
        s = df[col].astype(str).str
        if op == "replace":
            df[col] = s.replace(self.params.get("find", ""), self.params.get("replace", ""))
        else:
            df[col] = getattr(s, op)()
        return df

    def codegen(self, input_vars):
        v, col, op = input_vars[0], self.params["column"].strip(), self.params.get("op", "upper")
        if op not in self.allowed_options("op"):
            raise ValueError("invalid op: %s" % op)
        if op == "replace":
            return "%s.assign(%s=%s[%r].astype(str).str.replace(%r, %r))" % (
                v, col, v, col, self.params.get("find", ""), self.params.get("replace", ""))
        return "%s.assign(%s=%s[%r].astype(str).str.%s())" % (v, col, v, col, op)

    def output_columns(self, input_schemas):
        return input_schemas[0] if input_schemas else None


@register
class DateExtract(BaseNode):
    category = "transform"
    display_name = "Date Part"
    description = "Extract a part (year, month, ...) from a date column into a new column"
    param_schema = [
        {"name": "column", "type": "text", "label": "Date Column", "required": True},
        {"name": "part", "type": "select", "label": "Part",
         "options": ["year", "month", "day", "dayofweek", "hour"], "default": "year"},
        {"name": "name", "type": "text", "label": "New Column Name", "required": True},
    ]

    def execute(self, inputs):
        df = inputs[0].copy()
        col, part = self.params["column"].strip(), self.params.get("part", "year")
        if part not in self.allowed_options("part"):
            raise ValueError("invalid part: %s" % part)
        df[self.params["name"]] = getattr(pd.to_datetime(df[col]).dt, part)
        return df

    def codegen(self, input_vars):
        v = input_vars[0]
        part = self.params.get("part", "year")
        if part not in self.allowed_options("part"):
            raise ValueError("invalid part: %s" % part)
        return "%s.assign(%s=lambda d: pd.to_datetime(d[%r]).dt.%s)" % (
            v, self.params["name"], self.params["column"].strip(), part)

    def output_columns(self, input_schemas):
        if not input_schemas:
            return None
        return input_schemas[0] + [self.params["name"]]


@register
class ConditionalColumn(BaseNode):
    category = "transform"
    display_name = "Conditional Column"
    description = "New column: value_if_true where condition holds, else value_if_false"
    param_schema = [
        {"name": "name", "type": "text", "label": "Column Name", "required": True},
        {"name": "condition", "type": "text", "label": "Condition (safe expression)",
         "required": True, "placeholder": "price > 100"},
        {"name": "value_if_true", "type": "text", "label": "Value if true", "required": True},
        {"name": "value_if_false", "type": "text", "label": "Value if false", "required": True},
    ]

    @staticmethod
    def _coerce(v):
        try:
            return int(v)
        except (ValueError, TypeError):
            try:
                return float(v)
            except (ValueError, TypeError):
                return v

    def execute(self, inputs):
        import numpy as np

        from flowpipe.safe_eval import safe_eval
        df = inputs[0].copy()
        cond = safe_eval(self.params["condition"], df)
        df[self.params["name"]] = np.where(
            cond, self._coerce(self.params["value_if_true"]),
            self._coerce(self.params["value_if_false"]))
        return df

    def codegen(self, input_vars):
        v, p = input_vars[0], self.params
        return "%s.assign(%s=lambda df: np.where(df.eval(%r), %r, %r))" % (
            v, p["name"], p["condition"],
            self._coerce(p["value_if_true"]), self._coerce(p["value_if_false"]))

    def output_columns(self, input_schemas):
        if not input_schemas:
            return None
        return input_schemas[0] + [self.params["name"]]


@register
class AssertValid(BaseNode):
    category = "transform"
    display_name = "Assert / Validate"
    description = "Fail the pipeline if a data-quality check is violated; passes data through"
    param_schema = [
        {"name": "min_rows", "type": "number", "label": "Minimum rows (blank = skip)", "default": ""},
        {"name": "no_nulls", "type": "text", "label": "Columns that must be non-null (comma)", "default": ""},
        {"name": "unique_key", "type": "text", "label": "Columns that must be unique (comma)", "default": ""},
    ]

    def execute(self, inputs):
        df = inputs[0]
        mr = str(self.params.get("min_rows", "")).strip()
        if mr and len(df) < int(mr):
            raise AssertionError("min_rows: have %d, need %s" % (len(df), mr))
        for col in _cols(self.params.get("no_nulls", "")):
            if col in df.columns and df[col].isna().any():
                raise AssertionError("no_nulls: column '%s' has nulls" % col)
        key = _cols(self.params.get("unique_key", ""))
        if key and df.duplicated(subset=key).any():
            raise AssertionError("unique_key: duplicates on %s" % key)
        return df

    def codegen(self, input_vars):
        return "%s  # AssertValid checks run in the engine; passthrough" % input_vars[0]

    def output_columns(self, input_schemas):
        return input_schemas[0] if input_schemas else None
