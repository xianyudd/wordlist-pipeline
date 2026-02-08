import argparse
import json
from pathlib import Path
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    words = [
        w.strip()
        for w in Path(args.inp).read_text(encoding="utf-8", errors="ignore").splitlines()
        if w.strip()
    ]

    prefix = Counter(w[0] for w in words)
    suffix = Counter(w[-1] for w in words)

    report = {
        "count": len(words),
        "top_prefix_20": prefix.most_common(20),
        "top_suffix_20": suffix.most_common(20),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[qc] report -> {out_path}")


if __name__ == "__main__":
    main()
