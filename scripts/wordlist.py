#!/usr/bin/env python3
from __future__ import annotations

import argparse
import heapq
import os
import random
import re
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@dataclass(frozen=True)
class SourceDef:
    type: str
    name: str
    ref: str


@dataclass
class AppConfig:
    stage3_dir: Path
    sources_file: Path


def parse_sources_file(sources_file: Path) -> List[SourceDef]:
    """
    Parse sources/sources.txt format:
      type  name  ref_or_url
    Ignores blank lines and lines starting with '#'.
    """
    if not sources_file.exists():
        raise typer.BadParameter(f"sources file not found: {sources_file}")

    out: List[SourceDef] = []
    for raw in sources_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 3:
            raise typer.BadParameter(f"bad sources line (expect 3 columns): {raw}")
        typ, name, ref = parts
        out.append(SourceDef(type=typ, name=name, ref=ref))
    if not out:
        raise typer.BadParameter(f"no valid sources found in: {sources_file}")
    return out


def build_mapping(stage3_dir: Path, sources_file: Path) -> Dict[str, Path]:
    """
    Map source name -> expected stage3 output file, i.e. {name}.txt
    """
    items = parse_sources_file(sources_file)
    return {it.name: stage3_dir / f"{it.name}.txt" for it in items}


def parse_csv(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def select_sources(mapping: Dict[str, Path], include: Optional[str], exclude: Optional[str]) -> List[str]:
    known = set(mapping.keys())
    inc = set(parse_csv(include))
    exc = set(parse_csv(exclude))

    bad_inc = inc - known
    bad_exc = exc - known
    if bad_inc:
        raise typer.BadParameter(f"Unknown --include: {sorted(bad_inc)}")
    if bad_exc:
        raise typer.BadParameter(f"Unknown --exclude: {sorted(bad_exc)}")

    if inc:
        selected = set(inc)
    else:
        selected = set(known)

    selected -= exc
    if not selected:
        raise typer.BadParameter("No sources selected after include/exclude.")
    return sorted(selected)


def iter_words(fp: Path) -> Iterable[str]:
    """
    Stream words line by line (trimmed, non-empty).
    """
    with fp.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip()
            if w:
                yield w


def load_set(fp: Path) -> Set[str]:
    """
    Load file into a set (dedup within file).
    """
    return set(iter_words(fp))


def count_lines(fp: Path) -> int:
    """
    Fast-ish line count (stream).
    """
    n = 0
    with fp.open("r", encoding="utf-8", errors="ignore") as f:
        for _ in f:
            n += 1
    return n


def reservoir_sample(iterable: Iterable[str], k: int, seed: int = 0) -> List[str]:
    """
    Reservoir sampling: sample k items from an iterable without storing all items.
    """
    rng = random.Random(seed)
    res: List[str] = []
    for i, item in enumerate(iterable, start=1):
        if i <= k:
            res.append(item)
        else:
            j = rng.randint(1, i)
            if j <= k:
                res[j - 1] = item
    return res


@app.callback()
def _global_options(
    ctx: typer.Context,
    dir: Path = typer.Option(Path("data/stage3_filtered"), "--dir", help="stage3 directory"),
    sources_file: Path = typer.Option(Path("sources/sources.txt"), "--sources-file", help="sources definition file"),
):
    ctx.obj = AppConfig(stage3_dir=dir, sources_file=sources_file)


@app.command("sources")
def cmd_sources(
    ctx: typer.Context,
    counts: bool = typer.Option(False, "--counts", help="also show line counts"),
    show_ref: bool = typer.Option(False, "--show-ref", help="also show ref_or_url column"),
):
    """
    List sources from sources.txt and their stage3 file status.
    """
    cfg: AppConfig = ctx.obj
    items = parse_sources_file(cfg.sources_file)
    mapping = build_mapping(cfg.stage3_dir, cfg.sources_file)

    table = Table(title="Sources", box=box.SIMPLE_HEAVY)
    table.add_column("name", style="bold")
    table.add_column("type")
    if show_ref:
        table.add_column("ref_or_url", overflow="fold")
    table.add_column("stage3_file", overflow="fold")
    table.add_column("status")
    if counts:
        table.add_column("count", justify="right")

    for it in items:
        fp = mapping[it.name]
        status = "OK" if fp.exists() else "MISSING"
        status_text = Text(status, style=("green" if status == "OK" else "red"))
        row = [it.name, it.type]
        if show_ref:
            row.append(it.ref)
        row.extend([fp.name, status_text])
        if counts:
            row.append(str(count_lines(fp)) if fp.exists() else "-")
        table.add_row(*row)

    console.print(table)


@app.command("stats")
def cmd_stats(
    ctx: typer.Context,
    include: Optional[str] = typer.Option(None, "--include", help="comma-separated source names"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="comma-separated source names"),
    pairwise: bool = typer.Option(True, "--pairwise/--no-pairwise", help="show pairwise intersections"),
    exclusive: bool = typer.Option(True, "--exclusive/--no-exclusive", help="show exclusive counts"),
):
    """
    Show counts / union / duplicates / pairwise intersections / exclusive counts.
    """
    cfg: AppConfig = ctx.obj
    mapping = build_mapping(cfg.stage3_dir, cfg.sources_file)
    selected = select_sources(mapping, include, exclude)

    # Load sets
    sets: Dict[str, Set[str]] = {}
    for name in selected:
        fp = mapping[name]
        if not fp.exists():
            raise typer.BadParameter(f"Missing stage3 file for {name}: {fp}")
        sets[name] = load_set(fp)

    # Per-source counts
    t1 = Table(title="Per-source counts", box=box.SIMPLE_HEAVY)
    t1.add_column("source", style="bold")
    t1.add_column("count", justify="right")
    for name in selected:
        t1.add_row(name, f"{len(sets[name]):,}")
    console.print(t1)

    union = set().union(*sets.values()) if sets else set()
    sum_counts = sum(len(s) for s in sets.values())
    duplicates = sum_counts - len(union)

    summary = Table(title="Summary", box=box.SIMPLE_HEAVY)
    summary.add_column("metric", style="bold")
    summary.add_column("value", justify="right")
    summary.add_row("Union (selected)", f"{len(union):,}")
    summary.add_row("Sum(counts)", f"{sum_counts:,}")
    summary.add_row("Cross-source duplicates", f"{duplicates:,}")
    console.print(summary)

    if pairwise and len(selected) >= 2:
        t2 = Table(title="Pairwise intersections", box=box.SIMPLE_HEAVY)
        t2.add_column("A", style="bold")
        t2.add_column("B", style="bold")
        t2.add_column("|A ∩ B|", justify="right")
        for a, b in combinations(selected, 2):
            t2.add_row(a, b, f"{len(sets[a] & sets[b]):,}")
        console.print(t2)

    if exclusive:
        t3 = Table(title="Exclusive counts (only in that source)", box=box.SIMPLE_HEAVY)
        t3.add_column("source", style="bold")
        t3.add_column("exclusive", justify="right")
        for a in selected:
            others = set().union(*[sets[b] for b in selected if b != a])
            only = sets[a] - others
            t3.add_row(a, f"{len(only):,}")
        console.print(t3)


@app.command("build")
def cmd_build(
    ctx: typer.Context,
    out: Path = typer.Option(..., "--out", help="output file"),
    include: Optional[str] = typer.Option(None, "--include", help="comma-separated source names"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="comma-separated source names"),
    sort_output: bool = typer.Option(True, "--sort/--no-sort", help="sort output wordlist"),
):
    """
    Merge selected sources and write output wordlist (dedup union).
    """
    cfg: AppConfig = ctx.obj
    mapping = build_mapping(cfg.stage3_dir, cfg.sources_file)
    selected = select_sources(mapping, include, exclude)

    missing = [name for name in selected if not mapping[name].exists()]
    if missing:
        raise typer.BadParameter(f"Missing stage3 file(s): {missing}")

    union: Set[str] = set()
    per: Dict[str, int] = {}

    for name in selected:
        s = load_set(mapping[name])
        per[name] = len(s)
        union |= s

    out.parent.mkdir(parents=True, exist_ok=True)
    if sort_output:
        data = "\n".join(sorted(union)) + ("\n" if union else "")
    else:
        # no-sort: faster, but output order is arbitrary
        data = "\n".join(union) + ("\n" if union else "")
    out.write_text(data, encoding="utf-8")

    table = Table(title="Build result", box=box.SIMPLE_HEAVY)
    table.add_column("source", style="bold")
    table.add_column("count", justify="right")
    for name in selected:
        table.add_row(name, f"{per[name]:,}")
    table.add_section()
    table.add_row("UNION", f"{len(union):,}")
    console.print(table)
    console.print(f"[bold green]Wrote[/bold green] {out}")


@app.command("head")
def cmd_head(
    ctx: typer.Context,
    n: int = typer.Option(30, "-n", help="how many words to print"),
    include: Optional[str] = typer.Option(None, "--include", help="comma-separated source names"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="comma-separated source names"),
):
    """
    Print the first N words of the merged union (lexicographically).
    Optimized: uses heapq.nsmallest instead of sorting the entire union.
    """
    cfg: AppConfig = ctx.obj
    mapping = build_mapping(cfg.stage3_dir, cfg.sources_file)
    selected = select_sources(mapping, include, exclude)

    union: Set[str] = set()
    for name in selected:
        fp = mapping[name]
        if not fp.exists():
            raise typer.BadParameter(f"Missing stage3 file for {name}: {fp}")
        union |= load_set(fp)

    for w in heapq.nsmallest(n, union):
        console.print(w)


@app.command("sample")
def cmd_sample(
    ctx: typer.Context,
    n: int = typer.Option(30, "-n", help="how many samples"),
    seed: int = typer.Option(0, "--seed", help="random seed"),
    include: Optional[str] = typer.Option(None, "--include", help="comma-separated source names"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="comma-separated source names"),
):
    """
    Print N random samples from merged union.
    Optimized: reservoir sampling (doesn't need to build a list of all words).
    """
    cfg: AppConfig = ctx.obj
    mapping = build_mapping(cfg.stage3_dir, cfg.sources_file)
    selected = select_sources(mapping, include, exclude)

    # Stream union by reading each file; still dedup via a set of seen.
    seen: Set[str] = set()

    def union_iter():
        for name in selected:
            fp = mapping[name]
            if not fp.exists():
                raise typer.BadParameter(f"Missing stage3 file for {name}: {fp}")
            for w in iter_words(fp):
                if w not in seen:
                    seen.add(w)
                    yield w

    samples = reservoir_sample(union_iter(), n, seed=seed)
    for w in samples:
        console.print(w)


@app.command("search")
def cmd_search(
    ctx: typer.Context,
    contains: Optional[str] = typer.Option(None, "--contains", help="substring match"),
    regex: Optional[str] = typer.Option(None, "--regex", help="regex match"),
    limit: int = typer.Option(50, "--limit", help="max rows to print"),
    include: Optional[str] = typer.Option(None, "--include", help="comma-separated source names"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="comma-separated source names"),
):
    """
    Search merged union by substring or regex; show first `limit` matches.
    """
    if not contains and not regex:
        raise typer.BadParameter("search requires --contains or --regex")

    cfg: AppConfig = ctx.obj
    mapping = build_mapping(cfg.stage3_dir, cfg.sources_file)
    selected = select_sources(mapping, include, exclude)

    pat = re.compile(regex) if regex else None

    # Stream union with dedup (avoid set union of 600k if you only need first limit)
    seen: Set[str] = set()
    hits: List[str] = []

    for name in selected:
        fp = mapping[name]
        if not fp.exists():
            raise typer.BadParameter(f"Missing stage3 file for {name}: {fp}")
        for w in iter_words(fp):
            if w in seen:
                continue
            seen.add(w)

            ok = False
            if pat:
                ok = bool(pat.search(w))
            else:
                ok = contains in w  # type: ignore[operator]

            if ok:
                hits.append(w)
                if len(hits) >= limit:
                    break
        if len(hits) >= limit:
            break

    hits.sort()
    table = Table(title="Search results", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column("word", style="bold")
    for i, w in enumerate(hits, start=1):
        table.add_row(str(i), w)

    console.print(table)
    console.print(f"[dim]shown {len(hits)} (limit={limit}), sources={selected}[/dim]")


if __name__ == "__main__":
    app()
