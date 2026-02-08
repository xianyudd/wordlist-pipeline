import argparse
from pathlib import Path
import re


def parse_sources_file(sources_file: Path) -> list[dict]:
    """
    Parse sources/sources.txt with format:
      type  name  ref_or_url
    Ignores blank lines and lines starting with '#'.
    """
    items = []
    for line in sources_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 3:
            raise SystemExit(f"Bad sources line (expect 3 columns): {line}")
        typ, name, ref = parts
        items.append({"type": typ, "name": name, "ref": ref})
    return items


def parse_csv(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def load_set(fp: Path) -> set[str]:
    return {
        w.strip()
        for w in fp.read_text(encoding="utf-8", errors="ignore").splitlines()
        if w.strip()
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input dir (e.g. data/stage3_filtered)")
    ap.add_argument("--out", required=True, help="output file (e.g. out/3zi_words.txt)")
    ap.add_argument("--sources-file", default="sources/sources.txt", help="sources definition file")
    ap.add_argument("--include", help="comma-separated source names (from sources file) to include")
    ap.add_argument("--exclude", help="comma-separated source names (from sources file) to exclude")
    ap.add_argument("--list-sources", action="store_true", help="list available sources and exit")
    args = ap.parse_args()

    inp = Path(args.inp)
    sources_file = Path(args.sources_file)

    if not sources_file.exists():
        raise SystemExit(f"sources-file not found: {sources_file}")

    items = parse_sources_file(sources_file)
    # mapping: source name -> expected stage3 file
    mapping: dict[str, Path] = {it["name"]: inp / f'{it["name"]}.txt' for it in items}
    known = list(mapping.keys())

    if args.list_sources:
        print(f"Sources from {sources_file}:")
        for name in known:
            fp = mapping[name]
            status = "OK" if fp.exists() else "MISSING"
            print(f"  - {name} -> {fp} [{status}]")
        return

    include = set(parse_csv(args.include))
    exclude = set(parse_csv(args.exclude))

    bad_inc = include - set(known)
    bad_exc = exclude - set(known)
    if bad_inc:
        raise SystemExit(f"Unknown --include: {sorted(bad_inc)}. Known: {sorted(known)}")
    if bad_exc:
        raise SystemExit(f"Unknown --exclude: {sorted(bad_exc)}. Known: {sorted(known)}")

    if include:
        selected = set(include)
    else:
        selected = set(known)
    selected -= exclude

    if not selected:
        raise SystemExit("No sources selected after include/exclude.")

    union: set[str] = set()
    per: dict[str, int] = {}
    missing: list[str] = []

    for name in sorted(selected):
        fp = mapping[name]
        if not fp.exists():
            missing.append(str(fp))
            continue
        s = load_set(fp)
        per[name] = len(s)
        union |= s

    if missing:
        raise SystemExit("Missing stage3 file(s): " + "; ".join(missing))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(sorted(union)) + ("\n" if union else ""), encoding="utf-8")

    print("[merge] selected sources:")
    for name in sorted(per):
        print(f"  - {name}: {per[name]}")
    print(f"[merge] union: {len(union)} -> {out_path}")


if __name__ == "__main__":
    main()
