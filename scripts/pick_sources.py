#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import typer
import questionary
from rich import box
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


@dataclass(frozen=True)
class SourceDef:
    typ: str
    name: str
    ref: str


def parse_sources_file(p: Path) -> List[SourceDef]:
    """
    Parse sources file lines:
      type  name  ref_or_url
    Ignores blank lines and lines starting with '#'.
    """
    if not p.exists():
        raise SystemExit(f"sources file not found: {p}")

    items: List[SourceDef] = []
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 3:
            raise SystemExit(f"bad sources line (expect 3 cols): {raw}")
        typ, name, ref = parts
        items.append(SourceDef(typ=typ, name=name, ref=ref))

    if not items:
        raise SystemExit(f"no sources found in: {p}")
    return items


def count_lines(fp: Path) -> int:
    n = 0
    with fp.open("r", encoding="utf-8", errors="ignore") as f:
        for _ in f:
            n += 1
    return n


def is_wiki_source(name: str) -> bool:
    return "wiki" in name.lower()


def write_out(out: str, csv: str) -> None:
    if out == "-" or out == "":
        print(csv)
    else:
        Path(out).write_text(csv + "\n", encoding="utf-8")


def parse_indices(inp: str, n: int) -> List[int]:
    """
    Parse like: "1,2,4" or "1 2 4" or "1-3,5"
    1-based indices.
    """
    inp = inp.strip()
    if not inp:
        return []
    tokens = re.split(r"[,\s]+", inp)
    idx: List[int] = []
    for t in tokens:
        if not t:
            continue
        if "-" in t:
            a, b = t.split("-", 1)
            if not a.isdigit() or not b.isdigit():
                raise ValueError(f"bad range token: {t}")
            ia, ib = int(a), int(b)
            if ia > ib:
                ia, ib = ib, ia
            for k in range(ia, ib + 1):
                idx.append(k)
        else:
            if not t.isdigit():
                raise ValueError(f"bad index token: {t}")
            idx.append(int(t))

    seen = set()
    out = []
    for i in idx:
        if i not in seen:
            seen.add(i)
            out.append(i)

    for i in out:
        if i < 1 or i > n:
            raise ValueError(f"index out of range: {i} (valid: 1..{n})")
    return out


def choose_preset_select(default: str = "core") -> str:
    """
    Non-popup single select list:
      - ↑↓ move
      - Enter confirm
      - also supports 1/2/3/4 shortcuts (use_shortcuts=True)
    """
    choices = [
        questionary.Choice(title="core  (non-wiki)", value="core"),
        questionary.Choice(title="all   (everything)", value="all"),
        questionary.Choice(title="wiki  (wiki-only)", value="wiki"),
        questionary.Choice(title="custom (pick by indices)", value="custom"),
    ]

    ans = questionary.select(
        "Choose preset (↑↓ move, Enter confirm)",
        choices=choices,
        default=default,
        use_shortcuts=True,
    ).ask()

    if ans is None:
        raise SystemExit("Cancelled.")
    return ans


@app.command()
def main(
    dir: Path = typer.Option(Path("data/stage3_filtered"), "--dir", help="stage3 dir"),
    sources_file: Path = typer.Option(Path("sources/sources.txt"), "--sources-file", help="sources definition file"),
    out: str = typer.Option("-", "--out", help="write selected csv to file, '-' for stdout"),
    menu: bool = typer.Option(True, "--menu/--no-menu", help="show preset menu and interactive selection"),
    preset: str = typer.Option("core", "--preset", help="preset when --no-menu: core|all|wiki|custom"),
    custom: Optional[str] = typer.Option(None, "--custom", help="when preset=custom: indices like '1,2,4'"),
    show_ref: bool = typer.Option(False, "--show-ref", help="show ref/url column"),
):
    """
    Pretty source picker:
    - prints a Rich table (index/name/count/status)
    - choose preset via non-popup select list (↑↓ + Enter)
    - custom selection by indices: e.g. 1,2,4 or 1-3,5
    - outputs comma-separated source names
    """
    stage3 = dir
    items = parse_sources_file(sources_file)

    rows = []
    for i, it in enumerate(items, start=1):
        fp = stage3 / f"{it.name}.txt"
        exists = fp.exists()
        cnt = count_lines(fp) if exists else None
        rows.append(
            {
                "idx": i,
                "name": it.name,
                "type": it.typ,
                "ref": it.ref,
                "file": fp,
                "exists": exists,
                "count": cnt,
                "is_wiki": is_wiki_source(it.name),
            }
        )

    table = Table(title="Pick Sources", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right", style="bold")
    table.add_column("name", style="bold")
    table.add_column("count", justify="right")
    table.add_column("status")
    table.add_column("type")
    if show_ref:
        table.add_column("ref_or_url", overflow="fold")

    for r in rows:
        status = Text("OK", style="green") if r["exists"] else Text("MISSING", style="red")
        cnt = f'{r["count"]:,}' if r["count"] is not None else "-"
        name_style = "bold cyan" if r["is_wiki"] else "bold"
        name_text = Text(r["name"], style=name_style)
        row = [str(r["idx"]), name_text, cnt, status, r["type"]]
        if show_ref:
            row.append(r["ref"])
        table.add_row(*row)

    console.print(table)

    core_names = [r["name"] for r in rows if not r["is_wiki"]]
    wiki_names = [r["name"] for r in rows if r["is_wiki"]]
    all_names = [r["name"] for r in rows]

    def pick_by_preset(p: str, custom_str: Optional[str]) -> List[str]:
        p = p.strip().lower()
        if p in ("core", "c"):
            return core_names
        if p in ("all", "a"):
            return all_names
        if p in ("wiki", "w"):
            return wiki_names
        if p in ("custom", "x"):
            if not custom_str:
                return []
            idxs = parse_indices(custom_str, len(rows))
            return [rows[i - 1]["name"] for i in idxs]
        raise ValueError(f"unknown preset: {p}")

    if menu:
        p = choose_preset_select(default="core")
        if p == "custom":
            s = Prompt.ask("Enter indices (e.g. 1,2,4 or 1-3,5)")
            try:
                chosen = pick_by_preset("custom", s)
            except Exception as e:
                raise SystemExit(f"bad custom selection: {e}")
        else:
            chosen = pick_by_preset(p, None)
    else:
        try:
            chosen = pick_by_preset(preset, custom)
        except Exception as e:
            raise SystemExit(str(e))

    # filter out missing files
    missing = []
    ok = []
    names_set = {r["name"] for r in rows}
    for name in chosen:
        if name not in names_set:
            missing.append(name)
            continue
        fp = stage3 / f"{name}.txt"
        if not fp.exists():
            missing.append(name)
        else:
            ok.append(name)

    if not ok:
        raise SystemExit("No valid sources selected (all missing or empty selection).")

    if missing:
        console.print(f"[yellow]Warning[/yellow]: skipped missing sources: {missing}")

    csv = ",".join(ok)
    console.print(f"\n[bold green]Selected[/bold green]: {csv}\n")
    write_out(out, csv)


if __name__ == "__main__":
    app()
