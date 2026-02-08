#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Check whether all words in A are contained in B.

Typical use:
  A = out/hanyuguoxue_changdu3_top50.txt       (≈5000)
  B = out/pick.words.like.txt                 (your pipeline output)

Outputs:
  - summary to stdout
  - optional missing list file (A \\ B) 
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Set


def read_lines(p: Path) -> List[str]:
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def to_set(lines: List[str]) -> Set[str]:
    return set(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="probe list (needles), one per line")
    ap.add_argument("--b", required=True, help="candidate list (haystack), one per line")
    ap.add_argument("--missing-out", default="out/missing_from_b.txt", help="write A\\B here")
    ap.add_argument("--report-out", default="out/contains_report.json", help="write json report here")
    args = ap.parse_args()

    a_path = Path(args.a)
    b_path = Path(args.b)

    a_lines = read_lines(a_path)
    b_lines = read_lines(b_path)

    a = to_set(a_lines)
    b = to_set(b_lines)

    missing = sorted(a - b)
    inter = len(a & b)

    report = {
        "a_path": str(a_path),
        "b_path": str(b_path),
        "a_total_lines": len(a_lines),
        "b_total_lines": len(b_lines),
        "a_unique": len(a),
        "b_unique": len(b),
        "intersection": inter,
        "missing_count": len(missing),
        "contains_all": len(missing) == 0,
    }

    print("=== Contains check ===")
    print(f"A (probe): {a_path}  lines={len(a_lines)} unique={len(a)}")
    print(f"B (cand) : {b_path}  lines={len(b_lines)} unique={len(b)}")
    print(f"Intersection: {inter}")
    print(f"Missing (A\\B): {len(missing)}")
    print(f"Contains all?  {report['contains_all']}")

    out_missing = Path(args.missing_out)
    out_missing.parent.mkdir(parents=True, exist_ok=True)
    out_missing.write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
    print(f"[OK] missing list -> {out_missing}")

    out_report = Path(args.report_out)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] report -> {out_report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
