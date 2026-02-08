#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple

BASE = "https://www.hanyuguoxue.com"
URL_TMPL = BASE + "/cidian/changdu-3-p{page}"

# Optional httpx; fallback to urllib
try:
    import httpx  # type: ignore
    HAS_HTTPX = True
except Exception:
    HAS_HTTPX = False

if not HAS_HTTPX:
    import urllib.request

CI_HREF_RE = re.compile(r"^/cidian/ci-[0-9a-f]+", re.IGNORECASE)


class H3TitleParser(HTMLParser):
    """Extract titles in <h3><a href="/cidian/ci-...">TITLE</a></h3>"""

    def __init__(self) -> None:
        super().__init__()
        self.in_h3 = False
        self.in_a = False
        self.buf: List[str] = []
        self.titles: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag == "h3":
            self.in_h3 = True
            return
        if tag == "a" and self.in_h3:
            href = None
            for k, v in attrs:
                if k.lower() == "href":
                    href = v
                    break
            if href and CI_HREF_RE.match(href):
                self.in_a = True
                self.buf = []

    def handle_data(self, data: str) -> None:
        if self.in_a:
            self.buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self.in_a:
            title = "".join(self.buf).strip()
            if title and title != "查看详情":
                self.titles.append(title)
            self.in_a = False
            self.buf = []
            return
        if tag == "h3":
            self.in_h3 = False


@dataclass
class CrawlResult:
    page: int
    count: int


def fetch_html(url: str, timeout: float = 20.0) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
        "Connection": "close",
    }

    if HAS_HTTPX:
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            r.encoding = r.encoding or "utf-8"
            return r.text

    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("latin-1", errors="replace")


def parse_titles(html: str) -> List[str]:
    p = H3TitleParser()
    p.feed(html)
    p.close()
    # dedup within page keep order
    seen = set()
    out: List[str] = []
    for t in p.titles:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def crawl(start: int, end: int, delay_min: float, delay_max: float, retries: int) -> tuple[list[CrawlResult], list[str]]:
    pages: List[CrawlResult] = []
    all_titles: List[str] = []
    global_seen = set()

    for page in range(start, end + 1):
        url = URL_TMPL.format(page=page)
        ok = False
        last_err: Optional[Exception] = None

        for attempt in range(1, retries + 1):
            try:
                html = fetch_html(url)
                titles = parse_titles(html)

                pages.append(CrawlResult(page=page, count=len(titles)))
                for t in titles:
                    if t not in global_seen:
                        global_seen.add(t)
                        all_titles.append(t)

                ok = True
                break
            except Exception as e:
                last_err = e
                backoff = min(2.0, 0.3 * (2 ** (attempt - 1)))
                time.sleep(backoff + random.random() * 0.2)

        if not ok:
            print(f"[ERROR] page={page} url={url} err={last_err}", file=sys.stderr)

        time.sleep(delay_min + random.random() * (delay_max - delay_min))

    return pages, all_titles


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=50)
    ap.add_argument("--out", type=str, default="data/raw/hanyuguoxue_changdu3_top50.txt")
    ap.add_argument("--report", type=str, default="data/raw/hanyuguoxue_changdu3_top50.report.json")
    ap.add_argument("--delay-min", type=float, default=0.15)
    ap.add_argument("--delay-max", type=float, default=0.35)
    ap.add_argument("--retries", type=int, default=4)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    pages, titles = crawl(args.start, args.end, args.delay_min, args.delay_max, args.retries)

    out_path.write_text("\n".join(titles) + ("\n" if titles else ""), encoding="utf-8")

    report = {
        "base": BASE,
        "url_template": URL_TMPL,
        "range": {"start": args.start, "end": args.end},
        "pages": [p.__dict__ for p in pages],
        "total_unique_titles": len(titles),
        "total_sum_counts": sum(p.count for p in pages),
        "note": "total_unique_titles is deduped across pages",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] wrote: {out_path}  (unique={len(titles)}, sum_pages={report['total_sum_counts']})")
    print(f"[OK] report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
