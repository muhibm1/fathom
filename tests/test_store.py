from datetime import UTC, datetime

import pytest

from orion.model import Confidence, Edge, EdgeKind, Event, EventKind, Node, NodeKind, Provenance
from orion.store import ProvenanceRequired, Store


def prov() -> Provenance:
    return Provenance(adapter="test", source="unit test")


def test_provenance_is_required():
    s = Store(":memory:")
    with pytest.raises(ProvenanceRequired):
        s.upsert_node(Node(NodeKind.MODEL, "a"))
    with pytest.raises(ProvenanceRequired):
        s.upsert_edge(Edge("model:a", "model:b", EdgeKind.CONSUMES))


def test_walk_keeps_tier_one_past_max_hops():
    s = Store(":memory:")
    names = ["a", "b", "c", "d", "e"]
    for n in names:
        s.upsert_node(Node(NodeKind.MODEL, n, provenance=[prov()]))
    s.upsert_node(Node(NodeKind.DASHBOARD, "dash", tier=1, provenance=[prov()]))
    # a <- b <- c <- d <- e <- dash   (each consumes the previous)
    chain = names + ["dash"]
    for up, down in zip(chain, chain[1:], strict=False):
        kind_up = "dashboard" if up == "dash" else "model"
        kind_down = "dashboard" if down == "dash" else "model"
        s.upsert_edge(Edge(f"{kind_down}:{down}", f"{kind_up}:{up}", EdgeKind.CONSUMES, Confidence.PARSED, provenance=[prov()]))
    found = s.walk(["model:a"], max_hops=2)
    assert set(found) == {"model:b", "model:c", "dashboard:dash"}
    assert found["dashboard:dash"]["hops"] == 5


def test_ledger_is_append_only():
    s = Store(":memory:")
    ev = Event(EventKind.CHANGE_LANDED, datetime(2026, 1, 1, tzinfo=UTC), ["model:a"], source="git", source_ref="abc")
    first = s.append_event(ev)
    ev.payload = {"changed": True}
    second = s.append_event(ev)
    assert first == second
    stored = s.events_for(["model:a"])
    assert len(stored) == 1 and stored[0]["payload"] == {}
