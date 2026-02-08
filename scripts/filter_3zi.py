import argparse
import re
from pathlib import Path

# 严格：恰好 3 个汉字（CJK Unified Ideographs 基本区）
RE_3HAN = re.compile(r"^[\u4e00-\u9fff]{3}$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for f in inp.glob("*.txt"):
        keep: list[str] = []
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            w = line.strip()
            if RE_3HAN.match(w):
                keep.append(w)

        keep = sorted(set(keep))
        (out / f.name).write_text(
            "\n".join(keep) + ("\n" if keep else ""),
            encoding="utf-8",
        )
        print(f"[filter] {f.name}: {len(keep)}")


if __name__ == "__main__":
    main()
