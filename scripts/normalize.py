import argparse
import re
from pathlib import Path


def normalize_token(w: str) -> str:
    w = w.strip()
    # 删除所有空白（包含 tab/空格/换行）
    w = re.sub(r"\s+", "", w)
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for f in inp.glob("*.txt"):
        out_words: list[str] = []
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            w = normalize_token(line)
            if w:
                out_words.append(w)

        out_words = sorted(set(out_words))
        (out / f.name).write_text(
            "\n".join(out_words) + ("\n" if out_words else ""),
            encoding="utf-8",
        )
        print(f"[normalize] {f.name}: {len(out_words)}")


if __name__ == "__main__":
    main()
