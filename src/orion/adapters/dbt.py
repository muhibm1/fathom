"""dbt adapter: manifest.json (+ catalog.json when present) to graph.

Emits models, seeds, snapshots, sources, exposures, teams, columns and the
edges between them. Column lineage is computed with sqlglot from the model
SQL, so it needs no warehouse connection.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..lineage import column_lineage, dejinja, schema_key
from ..model import Confidence, Edge, EdgeKind, Node, NodeKind, Provenance, node_id
from . import Emitted, repo_relative

ADAPTER = "dbt"

EXPOSURE_KIND = {"dashboard": NodeKind.DASHBOARD}


def _meta(d: dict) -> dict:
    meta = dict(d.get("meta") or {})
    meta.update((d.get("config") or {}).get("meta") or {})
    return meta


def _owner_node(owner: str, prov: Provenance) -> Node:
    kind = NodeKind.TEAM if owner.startswith("team/") else NodeKind.PERSON
    return Node(kind=kind, name=owner, provenance=[prov])


def load(project_dir: Path, repo_root: Path) -> Emitted:
    out = Emitted()
    target = project_dir / "target"
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} not found; run `dbt parse` or `dbt build` first")
    manifest = json.loads(manifest_path.read_text())
    catalog_path = target / "catalog.json"
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {"nodes": {}, "sources": {}}
    prov = Provenance(adapter=ADAPTER, source=repo_relative(manifest_path, repo_root))

    unique_to_graph: dict[str, str] = {}  # dbt unique_id -> graph node id
    sql_by_graph: dict[str, str] = {}
    schema: dict[str, dict[str, str]] = {}
    owners: set[str] = set()

    # --- sources
    for uid, src in manifest.get("sources", {}).items():
        name = f"{src['source_name']}.{src['name']}"
        meta = _meta(src)
        source_meta = _meta(manifest["sources"][uid].get("source_meta", {}) and {"meta": src.get("source_meta")})
        owner = meta.get("owner") or source_meta.get("owner")
        tier = meta.get("tier") or source_meta.get("tier")
        cols = {c["name"]: c.get("type", "") for c in catalog.get("sources", {}).get(uid, {}).get("columns", {}).values()}
        node = Node(
            kind=NodeKind.SOURCE_TABLE,
            name=name,
            properties={
                "path": repo_relative(project_dir / src.get("original_file_path", ""), repo_root),
                "database": src.get("database"),
                "schema": src.get("schema"),
                "identifier": src.get("identifier"),
                "description": src.get("description", ""),
                "meta": meta,
                "columns": sorted(cols),
            },
            tier=int(tier) if tier is not None else None,
            owner=owner,
            provenance=[prov],
        )
        out.nodes.append(node)
        unique_to_graph[uid] = node.id
        if cols:
            schema[schema_key(name)] = cols
        if owner:
            owners.add(owner)
            out.edges.append(Edge(node.id, node_id(NodeKind.TEAM if owner.startswith("team/") else NodeKind.PERSON, owner), EdgeKind.OWNED_BY, Confidence.DECLARED, provenance=[prov]))

    # --- models, seeds, snapshots
    kind_map = {"model": NodeKind.MODEL, "seed": NodeKind.SEED, "snapshot": NodeKind.SNAPSHOT}
    for uid, n in manifest.get("nodes", {}).items():
        if n.get("resource_type") not in kind_map:
            continue
        kind = kind_map[n["resource_type"]]
        meta = _meta(n)
        owner = meta.get("owner")
        tier = meta.get("tier")
        cat_cols = {c["name"]: c.get("type", "") for c in catalog.get("nodes", {}).get(uid, {}).get("columns", {}).values()}
        declared_cols = {c["name"]: "" for c in (n.get("columns") or {}).values()}
        cols = cat_cols
        node = Node(
            kind=kind,
            name=n["name"],
            properties={
                "path": repo_relative(project_dir / n.get("original_file_path", ""), repo_root),
                "materialized": (n.get("config") or {}).get("materialized"),
                "tags": n.get("tags", []),
                "description": n.get("description", ""),
                "schema": n.get("schema"),
                "alias": n.get("alias"),
                "contract": bool(meta.get("contract") or ((n.get("config") or {}).get("contract") or {}).get("enforced")),
                "meta": meta,
                "tests": [t for t in manifest.get("child_map", {}).get(uid, []) if t.startswith("test.")],
                "columns": sorted(cols),
                "declared_columns": sorted(declared_cols),
            },
            tier=int(tier) if tier is not None else None,
            owner=owner,
            provenance=[prov],
        )
        out.nodes.append(node)
        unique_to_graph[uid] = node.id
        if cols:
            schema[schema_key(n["name"])] = cols
        if kind is NodeKind.MODEL and n.get("raw_code"):
            sql_by_graph[node.id] = dejinja(n["raw_code"])
        if owner:
            owners.add(owner)
            out.edges.append(Edge(node.id, node_id(NodeKind.TEAM if owner.startswith("team/") else NodeKind.PERSON, owner), EdgeKind.OWNED_BY, Confidence.DECLARED, provenance=[prov]))

    # --- a seed that materialises the relation a source points at is the same table
    seeds_by_identifier = {n.name: n.id for n in out.nodes if n.kind is NodeKind.SEED}
    for n in list(out.nodes):
        if n.kind is NodeKind.SOURCE_TABLE and n.properties.get("identifier") in seeds_by_identifier:
            out.edges.append(Edge(n.id, seeds_by_identifier[n.properties["identifier"]], EdgeKind.CONSUMES, Confidence.INFERRED, {"via": "same relation"}, provenance=[prov]))

    # --- model-level lineage from parent_map
    for uid, parents in manifest.get("parent_map", {}).items():
        if uid not in unique_to_graph:
            continue
        for p in parents:
            if p in unique_to_graph:
                out.edges.append(Edge(unique_to_graph[uid], unique_to_graph[p], EdgeKind.CONSUMES, Confidence.PARSED, provenance=[prov]))

    # --- exposures
    for uid, ex in manifest.get("exposures", {}).items():
        meta = _meta(ex)
        owner = meta.get("owner") or (ex.get("owner") or {}).get("name")
        tier = meta.get("tier")
        kind = EXPOSURE_KIND.get(ex.get("type"), NodeKind.REPORT)
        node = Node(
            kind=kind,
            name=ex["name"],
            properties={
                "path": repo_relative(project_dir / ex.get("original_file_path", ""), repo_root),
                "exposure": True,
                "exposure_type": ex.get("type"),
                "maturity": ex.get("maturity"),
                "description": ex.get("description", ""),
                "sla": meta.get("sla"),
                "meta": meta,
                "url": ex.get("url"),
            },
            tier=int(tier) if tier is not None else None,
            owner=owner,
            provenance=[prov],
        )
        out.nodes.append(node)
        unique_to_graph[uid] = node.id
        for dep in (ex.get("depends_on") or {}).get("nodes", []):
            if dep in unique_to_graph:
                out.edges.append(Edge(node.id, unique_to_graph[dep], EdgeKind.CONSUMES, Confidence.DECLARED, provenance=[prov]))
        if owner:
            owners.add(owner)
            out.edges.append(Edge(node.id, node_id(NodeKind.TEAM if owner.startswith("team/") else NodeKind.PERSON, owner), EdgeKind.OWNED_BY, Confidence.DECLARED, provenance=[prov]))

    for owner in sorted(owners):
        out.nodes.append(_owner_node(owner, prov))

    # --- column nodes and column lineage
    # Models missing from the catalog (ephemeral, or never built) get their
    # columns from SQL. Passes repeat until nothing new resolves, so a model is
    # inferred after the models it reads from.
    from ..lineage import output_columns

    pending = {gid: sql for gid, sql in sql_by_graph.items() if schema_key(gid.split(":", 1)[1]) not in schema}
    for _ in range(len(pending) + 1):
        progressed = False
        for gid, sql in list(pending.items()):
            key = schema_key(gid.split(":", 1)[1])
            try:
                cols = output_columns(sql, schema)
            except Exception as e:  # noqa: BLE001
                out.notes.append(f"{gid}: could not infer columns ({e})")
                pending.pop(gid)
                continue
            if cols and "*" not in cols:
                schema[key] = {c: "" for c in cols}
                pending.pop(gid)
                progressed = True
        if not progressed:
            break
    for gid in pending:
        out.notes.append(f"{gid}: columns unknown (select * without a catalog); run `dbt docs generate`")
    for node in out.nodes:
        if node.kind in (NodeKind.MODEL, NodeKind.SEED, NodeKind.SNAPSHOT) and not node.properties.get("columns"):
            inferred = schema.get(schema_key(node.name))
            if inferred:
                node.properties["columns"] = sorted(inferred)
                node.properties["columns_source"] = "sql"

    col_prov = Provenance(adapter=ADAPTER, source="sqlglot column lineage over model SQL")
    for gid, sql in sql_by_graph.items():
        name = gid.split(":", 1)[1]
        lin = column_lineage(sql, schema)
        if lin.error:
            out.notes.append(f"{gid}: {lin.error}")
        for col in lin.columns:
            cnode = Node(NodeKind.COLUMN, f"{name}.{col}", properties={"asset": gid}, provenance=[col_prov])
            out.nodes.append(cnode)
            out.edges.append(Edge(cnode.id, gid, EdgeKind.COLUMN_OF, Confidence.PARSED, provenance=[col_prov]))
            for table, src_col in lin.derives.get(col, set()):
                src_asset = _asset_id_for_table(table, unique_to_graph)
                if src_asset is None:
                    continue
                src_name = src_asset.split(":", 1)[1]
                src_col_node = Node(NodeKind.COLUMN, f"{src_name}.{src_col}", properties={"asset": src_asset}, provenance=[col_prov])
                out.nodes.append(src_col_node)
                out.edges.append(Edge(src_col_node.id, src_asset, EdgeKind.COLUMN_OF, Confidence.PARSED, provenance=[col_prov]))
                out.edges.append(Edge(cnode.id, src_col_node.id, EdgeKind.DERIVES_FROM, Confidence.PARSED, provenance=[col_prov]))
    return out


def _asset_id_for_table(table: str, unique_to_graph: dict[str, str]) -> str | None:
    ids = set(unique_to_graph.values())
    for kind in (NodeKind.MODEL, NodeKind.SEED, NodeKind.SNAPSHOT, NodeKind.SOURCE_TABLE):
        cand = node_id(kind, table)
        if cand in ids:
            return cand
    return None
