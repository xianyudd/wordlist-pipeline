#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


@dataclass(frozen=True)
class SourceDef:
    typ: str
    name: str
    ref: str


def parse_sources_file(p: Path) -> List[SourceDef]:
    if not p.exists():
        raise FileNotFoundError(f"sources file not found: {p}")
    out: List[SourceDef] = []
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 3:
            raise ValueError(f"bad sources line (expect 3 columns): {raw}")
        typ, name, ref = parts
        out.append(SourceDef(typ=typ, name=name, ref=ref))
    return out


def write_list(out_path: Path, words: Iterable[str]) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen: Set[str] = set()
    buf: List[str] = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if w in seen:
            continue
        seen.add(w)
        buf.append(w)
    out_path.write_text("\n".join(buf) + ("\n" if buf else ""), encoding="utf-8")
    return len(buf)


def iter_lines(fp: Path) -> Iterable[str]:
    with fp.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s:
                yield s


def extract_plain_text(raw_dir: Path, name: str) -> Iterable[str]:
    # Prefer <name>.txt, fallback <name>
    cand1 = raw_dir / f"{name}.txt"
    cand2 = raw_dir / name
    if cand1.exists():
        return iter_lines(cand1)
    if cand2.exists():
        return iter_lines(cand2)
    raise FileNotFoundError(f"plain source not found: {cand1} or {cand2}")


def extract_thuocl(raw_dir: Path) -> Iterable[str]:
    base = raw_dir / "THUOCL"
    files = list((base / "data").glob("*.txt"))
    if not files:
        # fallback: search repo recursively for txt
        files = list(base.rglob("*.txt"))
    for fp in files:
        for line in iter_lines(fp):
            # format: word\tfreq
            w = line.split("\t", 1)[0].strip()
            if w:
                yield w


def extract_jieba(raw_dir: Path) -> Iterable[str]:
    base = raw_dir / "jieba"
    # common locations:
    cands = [
        base / "jieba" / "dict.txt",
        base / "dict.txt",
        base / "jieba" / "dict.txt.big",
        base / "dict.txt.big",
    ]
    fp = next((p for p in cands if p.exists()), None)
    if fp is None:
        # fallback: any dict.txt*
        hits = list(base.rglob("dict.txt*"))
        fp = hits[0] if hits else None
    if fp is None:
        raise FileNotFoundError("jieba dict file not found (dict.txt*)")

    for line in iter_lines(fp):
        # format: word freq pos
        w = line.split(None, 1)[0].strip()
        if w:
            yield w


def extract_opencc(raw_dir: Path) -> Iterable[str]:
    base = raw_dir / "OpenCC"
    # Prefer dictionary folder
    dict_dirs = [
        base / "data" / "dictionary",
        base / "data" / "dictionaries",
    ]
    files: List[Path] = []
    for d in dict_dirs:
        if d.exists():
            files.extend(d.rglob("*.txt"))
    if not files:
        files = list(base.rglob("*.txt"))

    for fp in files:
        for line in iter_lines(fp):
            if line.startswith("#"):
                continue
            # OpenCC lines often like: trad simp  (tab/space separated)
            parts = line.split()
            for token in parts:
                token = token.strip()
                if token:
                    yield token


def extract_zhwiki_titles(raw_dir: Path) -> Iterable[str]:
    fp = raw_dir / "zhwiki_titles_ns0_gz"
    if not fp.exists():
        # some people may keep .txt naming
        fp2 = raw_dir / "zhwiki_titles_ns0_gz.txt"
        if fp2.exists():
            fp = fp2
        else:
            raise FileNotFoundError(f"zhwiki titles not found: {fp}")
    return iter_lines(fp)


def extract_for_source(raw_dir: Path, src: SourceDef) -> Iterable[str]:
    name = src.name
    if name == "THUOCL":
        return extract_thuocl(raw_dir)
    if name == "jieba":
        return extract_jieba(raw_dir)
    if name == "OpenCC":
        return extract_opencc(raw_dir)
    if name == "zhwiki_titles_ns0_gz":
        return extract_zhwiki_titles(raw_dir)

    # Any extra sources (including: hanyuguoxue_changdu3_top50) treated as plain text
    return extract_plain_text(raw_dir, name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True, help="sources/sources.txt")
    ap.add_argument("--raw", required=True, help="data/raw")
    ap.add_argument("--out", required=True, help="data/stage1_extracted")
    args = ap.parse_args()

    sources_file = Path(args.sources)
    raw_dir = Path(args.raw)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = parse_sources_file(sources_file)
    if not sources:
        raise SystemExit("no sources found in sources file")

    for src in sources:
        out_path = out_dir / f"{src.name}.txt"
        words = extract_for_source(raw_dir, src)
        n = write_list(out_path, words)
        print(f"[extract] {src.name}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
