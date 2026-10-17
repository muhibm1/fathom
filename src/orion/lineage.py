"""Column-level lineage over dbt model SQL with sqlglot.

Jinja is reduced to plain SQL by substituting ``ref()`` and ``source()`` with
table names and stripping ``config()`` blocks. That covers the large majority
of dbt models; anything sqlglot cannot parse is reported, not guessed.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.lineage import lineage
from sqlglot.optimizer.qualify import qualify

REF_RE = re.compile(r"\{\{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}")
SOURCE_RE = re.compile(r"\{\{\s*source\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}")
CONFIG_RE = re.compile(r"\{\{\s*config\(.*?\)\s*\}\}", re.DOTALL)
JINJA_RE = re.compile(r"\{[{%#].*?[}%#]\}", re.DOTALL)


def source_table_name(source_name: str, table: str) -> str:
    return f"{source_name}.{table}"


def dejinja(raw_sql: str) -> str:
    sql = CONFIG_RE.sub("", raw_sql)
    sql = REF_RE.sub(lambda m: m.group(1), sql)
    sql = SOURCE_RE.sub(lambda m: f"{m.group(1)}__{m.group(2)}", sql)
    sql = JINJA_RE.sub("", sql)
    return sql.strip()


def schema_key(name: str) -> str:
    """Sources are keyed ``raw.raw_events`` in the graph but ``raw__raw_events`` in SQL."""
    return name.replace(".", "__")


def graph_name(key: str) -> str:
    return key.replace("__", ".", 1) if "__" in key else key


@dataclass
class ColumnLineage:
    columns: list[str] = field(default_factory=list)
    derives: dict[str, set[tuple[str, str]]] = field(default_factory=dict)  # col -> {(table, col)}
    error: str | None = None


def output_columns(sql: str, schema: dict[str, dict[str, str]], dialect: str = "duckdb") -> list[str]:
    expr = sqlglot.parse_one(sql, read=dialect)
    with contextlib.suppress(SqlglotError):
        expr = qualify(expr, schema=schema, dialect=dialect, validate_qualify_columns=False)
    return [c for c in expr.named_selects if c]


def column_lineage(sql: str, schema: dict[str, dict[str, str]], dialect: str = "duckdb") -> ColumnLineage:
    out = ColumnLineage()
    try:
        out.columns = output_columns(sql, schema, dialect)
    except SqlglotError as e:
        out.error = f"parse: {e}"
        return out
    for col in out.columns:
        try:
            node = lineage(col, sql, schema=schema, dialect=dialect)
        except SqlglotError as e:
            out.error = f"lineage {col}: {e}"
            continue
        leaves: set[tuple[str, str]] = set()
        for n in node.walk():
            if n.downstream:
                continue
            src = n.source
            if isinstance(src, exp.Table):
                table = src.name
                colname = n.name.split(".")[-1]
                leaves.add((graph_name(table), colname))
        out.derives[col] = leaves
    return out
