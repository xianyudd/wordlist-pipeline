# zhwiki_titles_ns0_gz

## 基本信息

- `name`: `zhwiki_titles_ns0_gz`
- `type`: `url`
- `source`: `https://dumps.wikimedia.org/zhwiki/latest/zhwiki-latest-all-titles-in-ns0.gz`

## 下载方式

由 `scripts/download.sh` 执行：

1. 下载：

```bash
curl -L --fail --retry 5 --retry-delay 1 \
  -o data/raw/zhwiki_titles_ns0_gz.gz \
  https://dumps.wikimedia.org/zhwiki/latest/zhwiki-latest-all-titles-in-ns0.gz
```

2. 解压为纯文本：

```bash
gzip -dc data/raw/zhwiki_titles_ns0_gz.gz > data/raw/zhwiki_titles_ns0_gz
```

## 原始数据格式

- 每行一个词条/标题（来自维基标题命名空间 0）
- 数据量大，是总词量主要来源之一

## 抽取规则

`scripts/extract.py` 在 `extract_zhwiki_titles()` 中：

- 直接按纯文本逐行读取
- 优先读取 `data/raw/zhwiki_titles_ns0_gz`
- 若不存在则尝试 `data/raw/zhwiki_titles_ns0_gz.txt`

抽取结果写入：

- `data/stage1_extracted/zhwiki_titles_ns0_gz.txt`

## 注意事项

- 该源规模较大，可能包含实体名、地名、站名等大量专有词。
- 若想控制词表风格，可在合并时排除：

```bash
make merge MERGE_EXCLUDE=zhwiki_titles_ns0_gz
```
