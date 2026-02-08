# hanyuguoxue_changdu3_top50

## 基本信息

- `name`: `hanyuguoxue_changdu3_top50`
- `type`: `gen`
- `source`: `https://www.hanyuguoxue.com/cidian/changdu-3-p{page}`

## 生成方式

该源不是下载静态文件，而是抓取网页分页结果，由 `scripts/download.sh` 调用：

```bash
python scripts/crawl_hanyuguoxue_top50.py \
  --start 1 --end 50 \
  --out data/raw/hanyuguoxue_changdu3_top50.txt \
  --report data/raw/hanyuguoxue_changdu3_top50.report.json
```

## 抓取规则（脚本内）

`scripts/crawl_hanyuguoxue_top50.py`：

- 访问 `/cidian/changdu-3-p{page}`（默认 1..50 页）
- 从 `<h3><a href="/cidian/ci-...">词条</a></h3>` 中提取标题
- 全局去重后输出词条列表
- 同时写报告文件（每页数量、总计等）

## 原始数据产物

- 词条文件：`data/raw/hanyuguoxue_changdu3_top50.txt`
- 报告文件：`data/raw/hanyuguoxue_changdu3_top50.report.json`

## 抽取规则

`scripts/extract.py` 将该源按“纯文本一行一词”处理（通用分支）：

- 优先读取 `data/raw/hanyuguoxue_changdu3_top50.txt`
- 写出 `data/stage1_extracted/hanyuguoxue_changdu3_top50.txt`

## 注意事项

- 该源名称含“changdu3”，与项目目标（三字词）一致。
- 如果本地已有输出文件，`download.sh` 默认跳过重复抓取。
