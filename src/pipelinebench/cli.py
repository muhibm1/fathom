"""The ``pipelinebench`` command."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from orion.config import load_config
from orion.store import Store

from .agents import make_agent
from .conditions import CONDITIONS
from .generate import write as write_scenarios
from .runner import check_ground_truth, report, run, write_results
from .scenarios import load_scenarios

app = typer.Typer(help="PipelineBench: does context make agents safer on data pipelines?", no_args_is_help=True)
console = Console()
ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "pipelinebench" / "scenarios"
RESULTS = ROOT / "pipelinebench" / "results"


def _store(config: Path | None) -> tuple[Path, Store]:
    cfg = load_config(config, cwd=ROOT)
    return cfg.root, Store(cfg.path(cfg.db))


@app.command()
def generate(directory: Path = typer.Option(SCENARIOS, "--dir")):
    """Write the fifty scenario files from the generator (ground truth is hand-written there)."""
    paths = write_scenarios(directory)
    console.print(f"wrote {len(paths)} scenarios to {directory}")


@app.command("list")
def list_cmd(directory: Path = typer.Option(SCENARIOS, "--dir")):
    t = Table("id", "family", "expected", "cite", "title")
    for s in load_scenarios(directory):
        t.add_row(s.id, s.family, s.expected.decision, ",".join(s.expected.must_cite), s.title)
    console.print(t)


@app.command("check-ground-truth")
def check(directory: Path = typer.Option(SCENARIOS, "--dir"), config: Path | None = typer.Option(None, "--config", "-c"), as_json: bool = typer.Option(False, "--json")):
    """Compare Orion's verdicts to the hand-written expectations; list every disagreement."""
    root, store = _store(config)
    rows = check_ground_truth(load_scenarios(directory), repo_root=root, store=store)
    if as_json:
        typer.echo(json.dumps(rows, indent=1))
        return
    agree = sum(r["agree"] for r in rows)
    for r in rows:
        if not r["agree"]:
            console.print(f"[yellow]{r['scenario']}[/yellow] {r['title']}: expected {r['expected']}, orion {r['orion']}; fired {r['fired']}; missing cites {r['missing_cites']}; missing names {r['missing_names']}; unresolved {r['unresolved']}")
    console.print(f"{agree}/{len(rows)} scenarios agree with Orion")


@app.command("run")
def run_cmd(
    agent: list[str] = typer.Option(["scripted"], "--agent", help="scripted | claude[:model] | command:<exe>"),
    condition: list[str] = typer.Option(["all"], "--condition", help="none | repo | rag | orion | all"),
    seeds: int = typer.Option(1, "--seeds"),
    name: str | None = typer.Option(None, "--name", help="Results file name (default: timestamp)."),
    directory: Path = typer.Option(SCENARIOS, "--dir"),
    out: Path = typer.Option(RESULTS, "--out"),
    config: Path | None = typer.Option(None, "--config", "-c"),
):
    """Run agents across conditions and write results JSON and a markdown report."""
    root, store = _store(config)
    conds = list(CONDITIONS) if condition == ["all"] else condition
    agents = [make_agent(a) for a in agent]
    scenarios = load_scenarios(directory)
    with console.status("running") as status:
        res = run(scenarios, agents, conds, repo_root=root, store=store, seeds=seeds, progress=lambda a, c, s, g: status.update(f"{a} / {c} / {s}: {g['decided']} ({'ok' if g['decision_correct'] else 'wrong'})"))
    j, m = write_results(res, out, name)
    console.print(report(res))
    console.print(f"wrote {j} and {m}")


@app.command("report")
def report_cmd(results: Path):
    console.print(report(json.loads(results.read_text())))


if __name__ == "__main__":
    app()
