SHELL := bash
PY := python

RAW := data/raw
S1  := data/stage1_extracted
S2  := data/stage2_normalized
S3  := data/stage3_filtered
OUT := out
OUT_PLOTS := docs/plots

# 产物文件名可覆盖
OUT_WORDS ?= $(OUT)/3zi_words.txt
OUT_OVERLAP ?= $(OUT)/source_overlap.png
PLOT_MODE ?= upset
PLOT_TYPES ?= all
PLOT_OVERLAP_METRIC ?= jaccard

# 选源（来自 sources/sources.txt 的 name 列），可覆盖
MERGE_INCLUDE ?=
MERGE_EXCLUDE ?=

# sources 定义文件路径可覆盖
SOURCES_FILE ?= sources/sources.txt

# 交互式临时文件目录
TMP_DIR ?= .tmp

# 安全拼接参数（避免空展开导致多余 '\'）
INCLUDE_FLAG := $(if $(MERGE_INCLUDE),--include $(MERGE_INCLUDE),)
EXCLUDE_FLAG := $(if $(MERGE_EXCLUDE),--exclude $(MERGE_EXCLUDE),)

.PHONY: all download extract normalize filter merge qc sources stats venn plots mergei qci clean

all: qc

download:
	@mkdir -p $(RAW)
	bash scripts/download.sh

extract: download
	@mkdir -p $(S1)
	$(PY) scripts/extract.py --sources $(SOURCES_FILE) --raw $(RAW) --out $(S1)

normalize: extract
	@mkdir -p $(S2)
	$(PY) scripts/normalize.py --in $(S1) --out $(S2)

filter: normalize
	@mkdir -p $(S3)
	$(PY) scripts/filter_3zi.py --in $(S2) --out $(S3)

# 关键：merge 依赖 filter，确保 stage3 完整（包括新加的 hanyuguoxue 源）
merge: filter
	@mkdir -p $(OUT)
	$(PY) scripts/wordlist.py --dir $(S3) --sources-file $(SOURCES_FILE) build --out $(OUT_WORDS) $(INCLUDE_FLAG) $(EXCLUDE_FLAG)

qc: merge
	@mkdir -p $(OUT)
	$(PY) scripts/qc.py --in $(OUT_WORDS) --out $(OUT)/report.json

sources:
	@test -d $(S3) || (echo "stage3 dir not found: $(S3). Run: make filter (or make all) first." >&2; exit 1)
	$(PY) scripts/wordlist.py --dir $(S3) --sources-file $(SOURCES_FILE) sources --counts --show-ref

stats:
	@test -d $(S3) || (echo "stage3 dir not found: $(S3). Run: make filter (or make all) first." >&2; exit 1)
	$(PY) scripts/wordlist.py --dir $(S3) --sources-file $(SOURCES_FILE) stats $(INCLUDE_FLAG) $(EXCLUDE_FLAG)

venn:
	@test -d $(S3) || (echo "stage3 dir not found: $(S3). Run: make filter (or make all) first." >&2; exit 1)
	@mkdir -p $(OUT)
	$(PY) scripts/plot_sources_venn.py --dir $(S3) --sources-file $(SOURCES_FILE) --out $(OUT_OVERLAP) --mode $(PLOT_MODE) $(INCLUDE_FLAG) $(EXCLUDE_FLAG)

plots:
	@test -d $(S3) || (echo "stage3 dir not found: $(S3). Run: make filter (or make all) first." >&2; exit 1)
	@mkdir -p $(OUT_PLOTS)
	@types="$(PLOT_TYPES)"; \
	IFS=',' read -ra arr <<< "$$types"; \
	for t in "$${arr[@]}"; do \
		mode="$$(echo "$$t" | xargs)"; \
		case "$$mode" in \
			venn|upset|overlap|auto|all) ;; \
			*) echo "invalid PLOT_TYPES item: '$$mode'. valid: venn,upset,overlap,auto,all" >&2; exit 1 ;; \
		esac; \
		if [ "$$mode" = "all" ]; then \
			echo "[plots] mode=all -> $(OUT_PLOTS)/source_overlap.{upset,overlap[,venn]}.png"; \
			$(PY) scripts/plot_sources_venn.py --dir $(S3) --sources-file $(SOURCES_FILE) --out $(OUT_PLOTS)/source_overlap.png --mode all --overlap-metric $(PLOT_OVERLAP_METRIC) $(INCLUDE_FLAG) $(EXCLUDE_FLAG); \
		else \
			out_file="$(OUT_PLOTS)/source_overlap.$$mode.png"; \
			echo "[plots] mode=$$mode -> $$out_file"; \
			$(PY) scripts/plot_sources_venn.py --dir $(S3) --sources-file $(SOURCES_FILE) --out "$$out_file" --mode "$$mode" --overlap-metric $(PLOT_OVERLAP_METRIC) $(INCLUDE_FLAG) $(EXCLUDE_FLAG); \
		fi; \
	done

# 交互式选择源：只要求 stage3 已经存在（不会强制重跑全流程）
mergei:
	@test -d $(S3) || (echo "stage3 dir not found: $(S3). Run: make filter (or make all) first." >&2; exit 1)
	@mkdir -p $(OUT) $(TMP_DIR)
	@$(PY) scripts/pick_sources.py --dir $(S3) --sources-file $(SOURCES_FILE) --menu --out $(TMP_DIR)/include.csv
	@inc="$$(cat $(TMP_DIR)/include.csv)"; \
	echo "[mergei] include=$$inc"; \
	$(PY) scripts/wordlist.py --dir $(S3) --sources-file $(SOURCES_FILE) build --out $(OUT_WORDS) --include "$$inc"

qci: mergei
	@mkdir -p $(OUT)
	$(PY) scripts/qc.py --in $(OUT_WORDS) --out $(OUT)/report.json

clean:
	rm -rf data out $(TMP_DIR)
