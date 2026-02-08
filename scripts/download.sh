#!/usr/bin/env bash
set -euo pipefail

RAW_DIR="${RAW_DIR:-data/raw}"
mkdir -p "$RAW_DIR"

git_clone_or_skip() {
  local name="$1"
  local url="$2"
  local dst="$RAW_DIR/$name"
  if [[ -d "$dst/.git" ]]; then
    echo "[git] exists $name (skip update)"
    return 0
  fi
  echo "[git] clone $name"
  git clone --depth=1 "$url" "$dst"
}

download_or_skip() {
  local name="$1"
  local url="$2"
  local dst="$RAW_DIR/$name"
  if [[ -f "$dst" ]]; then
    echo "[url] exists $name"
    return 0
  fi
  echo "[url] download $name"
  curl -L --fail --retry 5 --retry-delay 1 -o "$dst" "$url"
}

# ---- git sources ----
git_clone_or_skip "THUOCL" "https://github.com/thunlp/THUOCL.git"
git_clone_or_skip "jieba"  "https://github.com/fxsjy/jieba.git"
git_clone_or_skip "OpenCC" "https://github.com/BYVoid/OpenCC.git"

# ---- url source: zhwiki titles ----
# Keep both gz and plain for idempotency
ZHWIKI_GZ="$RAW_DIR/zhwiki_titles_ns0_gz.gz"
ZHWIKI_TXT="$RAW_DIR/zhwiki_titles_ns0_gz"

if [[ -f "$ZHWIKI_TXT" ]]; then
  echo "[url] exists zhwiki_titles_ns0_gz"
else
  if [[ ! -f "$ZHWIKI_GZ" ]]; then
    download_or_skip "zhwiki_titles_ns0_gz.gz" "https://dumps.wikimedia.org/zhwiki/latest/zhwiki-latest-all-titles-in-ns0.gz"
  else
    echo "[url] exists zhwiki_titles_ns0_gz.gz"
  fi
  echo "[url] gunzip zhwiki_titles_ns0_gz"
  gzip -dc "$ZHWIKI_GZ" > "$ZHWIKI_TXT"
fi

# ---- generated source: hanyuguoxue top50 (≈5000) ----
HG_TXT="$RAW_DIR/hanyuguoxue_changdu3_top50.txt"
HG_REP="$RAW_DIR/hanyuguoxue_changdu3_top50.report.json"

if [[ -f "$HG_TXT" ]]; then
  echo "[gen] exists hanyuguoxue_changdu3_top50"
else
  echo "[gen] crawl hanyuguoxue_changdu3_top50 (pages 1..50)"
  python scripts/crawl_hanyuguoxue_top50.py --start 1 --end 50 --out "$HG_TXT" --report "$HG_REP"
fi
