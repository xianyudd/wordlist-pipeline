#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast


@dataclass(frozen=True)
class SourceDef:
    typ: str
    name: str
    ref: str


def parse_sources_file(p: Path) -> List[SourceDef]:
    if not p.exists():
        raise SystemExit(f"sources file not found: {p}")

    items: List[SourceDef] = []
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 3:
            raise SystemExit(f"bad sources line (expect 3 columns): {raw}")
        typ, name, ref = parts
        items.append(SourceDef(typ=typ, name=name, ref=ref))
    if not items:
        raise SystemExit(f"no valid sources found in: {p}")
    return items


def parse_csv(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def select_sources(items: List[SourceDef], include: Optional[str], exclude: Optional[str]) -> List[str]:
    names = [it.name for it in items]
    known = set(names)
    inc = set(parse_csv(include))
    exc = set(parse_csv(exclude))

    bad_inc = sorted(inc - known)
    bad_exc = sorted(exc - known)
    if bad_inc:
        raise SystemExit(f"Unknown --include source(s): {bad_inc}")
    if bad_exc:
        raise SystemExit(f"Unknown --exclude source(s): {bad_exc}")

    selected = [n for n in names if (not inc or n in inc) and n not in exc]
    if not selected:
        raise SystemExit("No sources selected after include/exclude.")
    return selected


def iter_words(fp: Path) -> Iterable[str]:
    with fp.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip()
            if w:
                yield w


def build_mask_counts(stage3_dir: Path, names: List[str]) -> Counter[int]:
    missing = [name for name in names if not (stage3_dir / f"{name}.txt").exists()]
    if missing:
        raise SystemExit(
            f"missing stage3 file(s): {missing}. "
            f"Run pipeline first, e.g. `make filter`."
        )

    word_mask: Dict[str, int] = {}
    for i, name in enumerate(names):
        bit = 1 << i
        fp = stage3_dir / f"{name}.txt"
        for word in iter_words(fp):
            word_mask[word] = word_mask.get(word, 0) | bit
    return Counter(word_mask.values())


def require_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise SystemExit(
            "matplotlib is required. Install with: pip install -e '.[viz]'"
        ) from e
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.grid": False,
            "font.sans-serif": [
                "Noto Sans CJK SC",
                "Microsoft YaHei",
                "SimHei",
                "WenQuanYi Zen Hei",
                "PingFang SC",
                "Heiti SC",
                "Arial Unicode MS",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
        }
    )
    return plt


def display_name(name: str) -> str:
    mapping = {
        "THUOCL": "清华词库",
        "jieba": "jieba词典",
        "OpenCC": "OpenCC词库",
        "zhwiki_titles_ns0_gz": "维基百科标题",
        "hanyuguoxue_changdu3_top50": "汉语国学(三字)",
    }
    return mapping.get(name, name)


def source_palette(names: List[str]) -> Dict[str, str]:
    colors = [
        "#1F77B4",
        "#FF7F0E",
        "#2CA02C",
        "#D62728",
        "#9467BD",
        "#8C564B",
        "#E377C2",
        "#7F7F7F",
        "#BCBD22",
        "#17BECF",
    ]
    return {name: colors[i % len(colors)] for i, name in enumerate(names)}


def degree_palette(max_degree: int) -> Dict[int, str]:
    # High-contrast, colorblind-friendly categorical palette
    # to make intersection-degree classes easier to distinguish.
    scale = [
        "#56B4E9",  # 1
        "#009E73",  # 2
        "#E69F00",  # 3
        "#D55E00",  # 4
        "#CC79A7",  # 5
        "#0072B2",  # 6+
    ]
    out: Dict[int, str] = {}
    for d in range(1, max_degree + 1):
        out[d] = scale[min(d - 1, len(scale) - 1)]
    return out


def draw_venn(names: List[str], mask_counts: Counter[int], out: Path, title: str, dpi: int) -> None:
    if len(names) not in (2, 3):
        raise SystemExit(
            f"Venn mode only supports 2 or 3 sources, got {len(names)}. "
            "Use --mode upset or reduce --include."
        )

    plt = require_matplotlib()
    try:
        from matplotlib_venn import venn2, venn3
    except ImportError as e:
        raise SystemExit(
            "matplotlib-venn is required. Install with: pip install -e '.[viz]'"
        ) from e

    if len(names) == 2:
        fig = plt.figure(figsize=(8, 6))
        venn2(
            subsets=(
                mask_counts.get(0b01, 0),
                mask_counts.get(0b10, 0),
                mask_counts.get(0b11, 0),
            ),
            set_labels=(display_name(names[0]), display_name(names[1])),
        )
    else:
        fig = plt.figure(figsize=(8, 8))
        venn3(
            subsets=(
                mask_counts.get(0b001, 0),
                mask_counts.get(0b010, 0),
                mask_counts.get(0b011, 0),
                mask_counts.get(0b100, 0),
                mask_counts.get(0b101, 0),
                mask_counts.get(0b110, 0),
                mask_counts.get(0b111, 0),
            ),
            set_labels=(display_name(names[0]), display_name(names[1]), display_name(names[2])),
        )

    plt.title(title)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)


def draw_upset(
    names: List[str],
    mask_counts: Counter[int],
    out: Path,
    title: str,
    dpi: int,
    max_intersections: Optional[int],
    total_words: int,
) -> int:
    if len(names) < 2:
        raise SystemExit("Need at least 2 sources to draw an overlap chart.")

    plt = require_matplotlib()
    try:
        import pandas as pd
        from upsetplot import UpSet
    except ImportError as e:
        raise SystemExit(
            "upsetplot/pandas are required for >3 sources. "
            "Install with: pip install -e '.[viz]'"
        ) from e

    items = [(mask, count) for mask, count in mask_counts.items() if mask != 0 and count > 0]
    total_intersections = len(items)
    degree_counts_all = Counter(bin(mask).count("1") for mask, _ in items)
    items.sort(key=lambda x: (-x[1], x[0]))
    if max_intersections is not None and max_intersections > 0:
        items = items[:max_intersections]

    tuples = []
    values = []
    for mask, count in items:
        if mask == 0 or count <= 0:
            continue
        tuples.append(tuple(bool(mask & (1 << i)) for i in range(len(names))))
        values.append(count)

    if not tuples:
        raise SystemExit("No overlap data to plot.")

    index = pd.MultiIndex.from_tuples(tuples, names=names)
    series = pd.Series(values, index=index, dtype="int64")

    fig_w = max(14, min(28, int(max(12, len(values)) * 0.95)))
    fig = plt.figure(figsize=(fig_w, 7))
    src_colors = source_palette(names)
    deg_colors = degree_palette(len(names))
    upset = UpSet(
        series,
        subset_size="sum",
        sort_by="cardinality",
        show_counts=cast(Any, False),
        # Keep matrix marks neutral; bars are recolored below by intersection degree.
        facecolor="#4B5563",
        other_dots_color=cast(Any, "#C4CAD6"),
        shading_color=cast(Any, "#F4F6FA"),
        element_size=38,
        intersection_plot_elements=8,
        totals_plot_elements=3,
    )
    with warnings.catch_warnings():
        # Silence known pandas/upsetplot chained-assignment FutureWarning noise.
        warnings.filterwarnings(
            "ignore",
            message="A value is trying to be set on a copy of a DataFrame or Series.*",
            category=FutureWarning,
            module=r"upsetplot\.plotting",
        )
        try:
            axes = upset.plot(fig=fig)
        except TypeError:
            # Backward compatibility for upsetplot versions without fig=.
            axes = upset.plot()
            fig = plt.gcf()

    intersections_ax = None
    totals_ax = None
    if isinstance(axes, dict):
        intersections_ax = axes.get("intersections")
        totals_ax = axes.get("totals")

    if intersections_ax is None:
        for ax in fig.axes:
            if "Intersection size" in ax.get_ylabel():
                intersections_ax = ax
                break
    if totals_ax is None:
        for ax in fig.axes:
            if ax is not intersections_ax and len(ax.patches) >= len(names):
                totals_ax = ax
                break

    # Color intersection bars by overlap degree (how many sources in that subset).
    sorted_series = series.sort_values(ascending=False)
    degrees = [sum(1 for x in idx if x) for idx in sorted_series.index]
    if intersections_ax is not None:
        max_v = max(values) if values else 0
        min_v = min(values) if values else 0
        if min_v > 0 and max_v / min_v >= 80:
            intersections_ax.set_yscale("log")
            intersections_ax.set_ylabel("交集规模（对数刻度）")
        else:
            intersections_ax.set_ylabel("交集规模")

        for patch, degree in zip(intersections_ax.patches, degrees):
            patch.set_facecolor(deg_colors.get(degree, "#2F6FDD"))
            patch.set_edgecolor("white")
            patch.set_linewidth(0.6)
        # Annotate all intersections above a practical threshold to keep readability.
        y_offsets = [0.02, 0.08, 0.14, 0.05]
        from matplotlib.patches import Rectangle

        for i, (patch_raw, val) in enumerate(zip(intersections_ax.patches, sorted_series.values)):
            if val < 1000:
                continue
            patch = cast(Rectangle, patch_raw)
            x = patch.get_x() + patch.get_width() / 2.0
            y = patch.get_height()
            if intersections_ax.get_yscale() == "log":
                y_text = y * (1.04 + y_offsets[i % len(y_offsets)])
            else:
                y_text = y + max(200, y * (0.012 + y_offsets[i % len(y_offsets)]))
            intersections_ax.text(
                x,
                y_text,
                f"{int(val):,}",
                ha="center",
                va="bottom",
                fontsize=9,
                color="#2B2D33",
            )

    # Color per-source total bars by source palette.
    if totals_ax is not None:
        source_sizes = [
            sum(c for mask, c in mask_counts.items() if mask & (1 << i))
            for i in range(len(names))
        ]
        min_src = min(source_sizes) if source_sizes else 0
        max_src = max(source_sizes) if source_sizes else 0
        if min_src > 0 and max_src / min_src >= 30:
            x0, x1 = totals_ax.get_xlim()
            is_reversed = x0 > x1
            min_pos = max(1.0, min_src * 0.8)
            max_pos = max(max_src * 1.05, min_pos * 10)
            totals_ax.set_xscale("log")
            if is_reversed:
                totals_ax.set_xlim(max_pos, min_pos)
            else:
                totals_ax.set_xlim(min_pos, max_pos)
            totals_ax.set_xlabel("来源规模（对数刻度）")
        else:
            totals_ax.set_xlabel("来源规模")

        labels = [t.get_text() for t in totals_ax.get_yticklabels()]
        if labels:
            totals_ax.set_yticklabels([display_name(x) for x in labels])
        label_map = {label: src_colors.get(label, "#5E6A7D") for label in labels}
        from matplotlib.patches import Rectangle

        for i, patch_raw in enumerate(totals_ax.patches):
            patch = cast(Rectangle, patch_raw)
            label = labels[i] if i < len(labels) else ""
            color = label_map.get(label)
            if color is None:
                fallback_name = names[i] if i < len(names) else names[i % len(names)]
                color = src_colors[fallback_name]
            patch.set_facecolor(color)
            patch.set_edgecolor("white")
            patch.set_linewidth(0.6)

        # Label every source-size bar.
        x0, x1 = totals_ax.get_xlim()
        is_reversed = x0 > x1
        for patch_raw in totals_ax.patches:
            patch = cast(Rectangle, patch_raw)
            val = abs(patch.get_width())
            if val <= 0:
                continue
            x_end = patch.get_x() + patch.get_width()
            y_mid = patch.get_y() + patch.get_height() / 2.0
            if totals_ax.get_xscale() == "log":
                x_text = x_end * (1.06 if is_reversed else 1.02)
            else:
                delta = abs(x1 - x0) * 0.01
                x_text = x_end + delta
            totals_ax.text(
                x_text,
                y_mid,
                f"{int(round(val)):,}",
                ha=("right" if is_reversed else "left"),
                va="center",
                fontsize=9,
                color="#2B2D33",
            )

    from matplotlib.patches import Patch

    src_handles = [Patch(facecolor=src_colors[n], label=display_name(n)) for n in names]
    present_degrees = list(range(1, len(names) + 1))
    deg_handles = [
        Patch(
            facecolor=deg_colors[d],
            label=f"{d}个来源（{degree_counts_all.get(d, 0)}组）",
        )
        for d in present_degrees
    ]

    # Place legends at bottom to free horizontal space for the main chart.
    fig.legend(
        handles=src_handles,
        title="来源",
        loc="lower center",
        bbox_to_anchor=(0.32, 0.01),
        ncol=min(3, len(src_handles)),
        frameon=False,
    )
    fig.legend(
        handles=deg_handles,
        title="交集阶数",
        loc="lower center",
        bbox_to_anchor=(0.74, 0.01),
        ncol=min(3, len(deg_handles)),
        frameon=False,
    )

    fig.suptitle(title, fontsize=17, fontweight="semibold", y=0.965)
    shown_text = f"Top {len(values)} / 全部 {total_intersections}"
    subtitle_x = 0.06
    subtitle_y = 0.93
    if intersections_ax is not None:
        box = intersections_ax.get_position()
        subtitle_x = box.x0 + 0.02
        subtitle_y = min(0.95, max(0.91, box.y1 + 0.035))
    fig.text(
        subtitle_x,
        subtitle_y,
        f"来源数: {len(names)} | 并集词数: {total_words:,} | 交集展示: {shown_text}",
        ha="left",
        va="center",
        fontsize=10.5,
        color="#4C566A",
    )
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.16, wspace=0.28, hspace=0.12)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    return len(values)


def pair_intersection(mask_counts: Counter[int], i: int, j: int) -> int:
    bi = 1 << i
    bj = 1 << j
    return sum(c for mask, c in mask_counts.items() if (mask & bi) and (mask & bj))


def draw_overlap_heatmap(
    names: List[str],
    mask_counts: Counter[int],
    out: Path,
    title: str,
    dpi: int,
    metric: str,
) -> None:
    plt = require_matplotlib()

    n = len(names)
    if n < 2:
        raise SystemExit("Need at least 2 sources to draw overlap heatmap.")

    sizes = source_counts(mask_counts, names)
    matrix: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                # De-emphasize diagonal cells to focus on cross-source overlap.
                matrix[i][j] = float("nan")
                continue
            inter = pair_intersection(mask_counts, i, j)
            si = sizes[names[i]]
            sj = sizes[names[j]]
            if metric == "jaccard":
                union = si + sj - inter
                matrix[i][j] = (inter / union) if union > 0 else 0.0
            elif metric == "overlap":
                base = min(si, sj)
                matrix[i][j] = (inter / base) if base > 0 else 0.0
            else:
                # containment: row source covered by column source
                matrix[i][j] = (inter / si) if si > 0 else 0.0

    off_vals = [matrix[i][j] for i in range(n) for j in range(n) if i != j]
    off_vals = [v for v in off_vals if v == v]  # drop NaN
    vmax = max(off_vals) if off_vals else 1.0
    vmax = max(vmax * 1.08, 0.01)

    fig_w = max(8, min(14, n * 1.9))
    fig_h = max(7, min(12, n * 1.55))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    cmap = plt.get_cmap("YlGnBu").copy()
    cmap.set_bad("#EEF2F7")
    im = ax.imshow(matrix, vmin=0.0, vmax=vmax, cmap=cmap)

    labels = [display_name(x) for x in names]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=22, ha="right")
    ax.set_yticklabels(labels)

    for i in range(n):
        for j in range(n):
            v = matrix[i][j]
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=11, color="#7B8794")
                continue
            txt = f"{v:.1%}"
            color = "white" if v >= vmax * 0.55 else "#1F2D3D"
            ax.text(j, i, txt, ha="center", va="center", fontsize=10, color=color)

    if metric == "jaccard":
        metric_name = "Jaccard重合度"
    elif metric == "overlap":
        metric_name = "Overlap系数"
    else:
        metric_name = "包含率（行被列覆盖）"
    ax.set_title(metric_name, fontsize=13, pad=12)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("重合度（非对角线自适应）", rotation=90)

    fig.suptitle(title, fontsize=16, fontweight="semibold", y=0.99, x=0.6)
    box = ax.get_position()
    subtitle_x = box.x0 + 0.23
    subtitle_y = min(0.955, max(0.91, box.y1 + 0.06))
    fig.text(
        subtitle_x,
        subtitle_y,
        f"指标: {metric_name} | 色阶范围: 0% - {vmax:.1%}",
        ha="left",
        va="center",
        fontsize=11,
        color="#4C566A",
    )
    fig.subplots_adjust(left=0.19, right=0.9, top=0.84, bottom=0.16)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)


def source_counts(mask_counts: Counter[int], names: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i, name in enumerate(names):
        bit = 1 << i
        out[name] = sum(c for mask, c in mask_counts.items() if mask & bit)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Draw source overlap chart from sources/sources.txt and stage3 files."
    )
    p.add_argument("--dir", default="data/stage3_filtered", help="stage3 directory")
    p.add_argument("--sources-file", default="sources/sources.txt", help="sources definition file")
    p.add_argument("--out", default="out/source_overlap.png", help="output image path")
    p.add_argument("--include", default=None, help="comma-separated source names")
    p.add_argument("--exclude", default=None, help="comma-separated source names")
    p.add_argument(
        "--mode",
        default="upset",
        choices=["auto", "venn", "upset", "overlap", "all"],
        help="default is upset; auto: venn for <=3 sources, overlap for >3; all: export multiple charts",
    )
    p.add_argument("--title", default=None, help="figure title")
    p.add_argument("--dpi", type=int, default=160, help="output dpi")
    p.add_argument(
        "--max-intersections",
        type=int,
        default=20,
        help="max intersections shown in upset mode (0 means show all)",
    )
    p.add_argument(
        "--overlap-metric",
        default="jaccard",
        choices=["jaccard", "overlap", "containment"],
        help="metric for overlap mode",
    )
    return p.parse_args()


def output_with_suffix(out: Path, suffix: str) -> Path:
    """
    out/source_overlap.png + upset -> out/source_overlap.upset.png
    """
    if out.suffix:
        return out.with_name(f"{out.stem}.{suffix}{out.suffix}")
    return out.with_name(f"{out.name}.{suffix}")


def main() -> None:
    args = parse_args()
    stage3_dir = Path(args.dir)
    sources_file = Path(args.sources_file)
    out = Path(args.out)

    items = parse_sources_file(sources_file)
    names = select_sources(items, include=args.include, exclude=args.exclude)
    if len(names) < 2:
        raise SystemExit("Need at least 2 sources to draw an overlap chart.")

    mask_counts = build_mask_counts(stage3_dir, names)
    total = sum(mask_counts.values())
    chosen_mode = args.mode
    if args.mode == "auto":
        chosen_mode = "venn" if len(names) <= 3 else "overlap"

    modes_to_render: List[str]
    if chosen_mode == "all":
        modes_to_render = ["upset", "overlap"]
        if len(names) <= 3:
            modes_to_render.insert(0, "venn")
    else:
        modes_to_render = [chosen_mode]

    generated: List[Path] = []
    for mode in modes_to_render:
        if mode == "overlap":
            default_kind = "重合度热力图"
        elif mode == "upset":
            default_kind = "UpSet集合图"
        else:
            default_kind = "Venn集合图"
        title = args.title or f"三字词表来源重叠图（{default_kind}，{len(names)}个来源）"
        out_i = out if len(modes_to_render) == 1 else output_with_suffix(out, mode)

        shown_intersections: Optional[int] = None
        if mode == "venn":
            draw_venn(names, mask_counts, out=out_i, title=title, dpi=args.dpi)
        elif mode == "overlap":
            draw_overlap_heatmap(
                names,
                mask_counts,
                out=out_i,
                title=title,
                dpi=args.dpi,
                metric=args.overlap_metric,
            )
        else:
            max_intersections = None if args.max_intersections == 0 else args.max_intersections
            shown_intersections = draw_upset(
                names,
                mask_counts,
                out=out_i,
                title=title,
                dpi=args.dpi,
                max_intersections=max_intersections,
                total_words=total,
            )
        generated.append(out_i)
        print(f"[plot] mode={mode} output={out_i}")
        if mode == "upset" and shown_intersections is not None:
            print(f"[plot] shown_intersections={shown_intersections}")

    print(f"[plot] selected={','.join(names)}")
    print(f"[plot] union={total:,}")
    if len(generated) > 1:
        print("[plot] generated files:")
        for p in generated:
            print(f"  - {p}")
    per = source_counts(mask_counts, names)
    print("[plot] per-source counts:")
    for name in names:
        print(f"  - {name}: {per[name]:,}")


if __name__ == "__main__":
    main()
