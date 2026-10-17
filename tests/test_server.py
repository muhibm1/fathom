import asyncio
from pathlib import Path

from orion.config import load_config
from orion.server import build_server

ROOT = Path(__file__).resolve().parents[1]


def test_server_exposes_six_tools(synced_store):
    cfg = load_config(ROOT / "orion.yaml")
    cfg.db = str(synced_store.path)
    cfg.root = ROOT
    server = build_server(cfg)
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == {"preflight", "explain", "history", "record_decision", "propose_constraint", "ask"}


def test_ask_is_graph_scoped(synced_store):
    from orion.retrieval import ask

    out = ask(synced_store, "why is events partitioned by event_date", ["source_table:raw.raw_events"])
    assert out["answer"] != "not recorded"
    assert any("INC-214" in c["source"] or "CON-014" in c["chunk"] for c in out["chunks"])
    assert all("[" in s for s in out["answer"].split("] ") if s)
    nothing = ask(synced_store, "what colour is the finance office carpet", ["model:fct_revenue"])
    assert nothing["answer"] == "not recorded" or nothing["chunks"]


def test_rankers_agree_on_the_obvious_question(synced_store):
    from orion.retrieval import HashEmbedder, ask

    q = "why was raw_events repartitioned and what went wrong"
    scope = ["source_table:raw.raw_events"]
    lexical = ask(synced_store, q, scope, ranker="bm25")
    hybrid = ask(synced_store, q, scope, ranker="hybrid", embedder=HashEmbedder())
    dense = ask(synced_store, q, scope, ranker="embedding", embedder=HashEmbedder())
    for out in (lexical, hybrid, dense):
        assert out["answer"] != "not recorded"
        assert any("INC-214" in c["source"] for c in out["chunks"][:3])
    assert hybrid["ranker"] == "hybrid"
    cached = synced_store.con.execute("SELECT count(*) FROM chunk_vectors WHERE model = 'hash-512'").fetchone()[0]
    assert cached > 0
