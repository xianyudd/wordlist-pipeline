SHELL := bash
PY := python

RAW := data/raw
S1  := data/stage1_extracted
S2  := data/stage2_normalized
S3  := data/stage3_filtered
OUT := out

# 产物文件名可覆盖
OUT_WORDS ?= $(OUT)/3zi_words.txt

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

.PHONY: all download extract normalize filter merge qc sources stats mergei qci clean

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
