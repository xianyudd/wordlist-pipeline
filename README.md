# wordlist-pipeline

用于构建“中文三字词表”的可复现流水线项目。  
核心流程：下载多源词库 -> 抽取 -> 规范化 -> 三字过滤 -> 合并 -> 质检报告。

## 项目特点

- 多数据源统一处理（THUOCL / jieba / OpenCC / zhwiki / 汉语国学抓取）。
- 全流程可复现（`make all` 一条命令）。
- 支持按来源筛选合并（`--include / --exclude`）。
- 支持交互式选源（`make mergei`）。
- 产出基础质检报告（词数、首字/尾字 Top20）。

## 目录结构

```text
.
├── Makefile
├── pyproject.toml
├── docs/
│   ├── README.md                  # 数据源文档索引
│   └── sources/
│       ├── THUOCL.md
│       ├── jieba.md
│       ├── OpenCC.md
│       ├── zhwiki_titles_ns0_gz.md
│       └── hanyuguoxue_changdu3_top50.md
├── sources/
│   └── sources.txt                # 数据源定义（type name ref/url）
├── scripts/
│   ├── download.sh                # 下载/抓取原始数据
│   ├── extract.py                 # 各源抽取到统一格式
│   ├── normalize.py               # 规范化（去空白、去重、排序）
│   ├── filter_3zi.py              # 严格保留 3 个汉字
│   ├── wordlist.py                # 源管理/统计/合并 CLI
│   ├── pick_sources.py            # 交互式选源
│   ├── qc.py                      # 质检报告
│   └── contains_check.py          # A 是否被 B 完整覆盖
├── data/
│   ├── raw/
│   ├── stage1_extracted/
│   ├── stage2_normalized/
│   └── stage3_filtered/
└── out/
    ├── 3zi_words.txt
    └── report.json
```

## 环境要求

- Python >= 3.10
- Bash（执行 `scripts/download.sh`）
- 网络访问（拉取 GitHub/Wikimedia/汉语国学网页）

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

或最小安装：

```bash
pip install typer rich questionary
```

## 快速开始

执行完整流水线：

```bash
make all
```

默认产物：

- `out/3zi_words.txt`：最终三字词表
- `out/report.json`：质检报告

## Make 命令说明

- `make download`：下载/抓取所有原始源到 `data/raw`
- `make extract`：抽取到 `data/stage1_extracted`
- `make normalize`：规范化到 `data/stage2_normalized`
- `make filter`：筛选为严格三字词到 `data/stage3_filtered`
- `make merge`：合并生成 `out/3zi_words.txt`
- `make qc`：生成 `out/report.json`
- `make sources`：查看来源状态、数量与引用信息
- `make stats`：查看集合统计（并集、交集、独占等）
- `make mergei`：交互式选择来源并合并
- `make qci`：交互式合并后立即做 QC
- `make clean`：清理 `data/`、`out/`、`.tmp/`

## 常用用法

### 1) 按来源筛选合并

只使用指定来源：

```bash
make merge MERGE_INCLUDE=THUOCL,jieba,OpenCC
```

排除 wiki 大源：

```bash
make merge MERGE_EXCLUDE=zhwiki_titles_ns0_gz
```

### 2) 统计与可视化检查

```bash
make sources
make stats
```

### 3) 交互式选源

```bash
make mergei
make qci
```

### 4) 覆盖率检查（A 是否都在 B 中）

例如检查汉语国学列表是否被最终词表覆盖：

```bash
python scripts/contains_check.py \
  --a data/raw/hanyuguoxue_changdu3_top50.txt \
  --b out/3zi_words.txt \
  --missing-out out/missing_from_b.txt \
  --report-out out/contains_report.json
```

## 数据源定义

`sources/sources.txt` 每行 3 列：

```text
type  name  ref_or_url
```

当前内置：

- `git THUOCL`
- `git jieba`
- `git OpenCC`
- `url zhwiki_titles_ns0_gz`
- `gen hanyuguoxue_changdu3_top50`

新增来源后，按以下约定即可接入流程：

1. 在 `sources/sources.txt` 新增一行。
2. 原始文件放到 `data/raw/<name>.txt`（或在 `extract.py` 里添加专用解析逻辑）。
3. 重新执行 `make extract normalize filter merge qc`。

## 数据源文档

每个数据源的详细介绍、格式和处理规则见：

- `docs/README.md`

## 关键脚本行为说明

- `extract.py`
  - 对 `THUOCL/jieba/OpenCC/zhwiki_titles_ns0_gz` 使用专用提取逻辑；
  - 其他源默认按纯文本一行一词处理（例如 `hanyuguoxue_changdu3_top50`）。
- `normalize.py`
  - 去除词内空白，按文件去重并排序。
- `filter_3zi.py`
  - 仅保留 `^[\u4e00-\u9fff]{3}$`，即“恰好 3 个基本汉字”。
- `wordlist.py`
  - 提供 `sources / stats / build / head` 等子命令；
  - `build` 阶段做并集去重，输出总词表。
- `qc.py`
  - 输出总词数、首字 Top20、尾字 Top20。

## 常见问题

- 下载慢或失败：
  - 先重试 `make download`，脚本自带基础重试；网络代理环境可自行配置 `git/curl`。
- `make sources` 提示 stage3 不存在：
  - 先执行 `make filter` 或 `make all`。
- 结果词数变化较大：
  - 检查是否启用了 `MERGE_INCLUDE / MERGE_EXCLUDE`，以及上游源是否更新。

## License

本仓库代码采用 [MIT License](LICENSE)。  
各第三方数据源与词库遵循其各自许可证，请在使用前自行核对。
