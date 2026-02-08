# THUOCL

## 基本信息

- `name`: `THUOCL`
- `type`: `git`
- `source`: `https://github.com/thunlp/THUOCL.git`

## 下载方式

由 `scripts/download.sh` 执行：

```bash
git clone --depth=1 https://github.com/thunlp/THUOCL.git data/raw/THUOCL
```

如果目录已存在且是 git 仓库，则跳过。

## 原始数据格式

主要读取 `data/raw/THUOCL/data/*.txt`。  
常见行格式为：

```text
词语<TAB>频次
```

## 抽取规则

`scripts/extract.py` 在 `extract_thuocl()` 中：

- 读取每行
- 按 `\t` 分割
- 取第一列作为词条

抽取结果写入：

- `data/stage1_extracted/THUOCL.txt`

## 注意事项

- 上游词表包含非三字词，最终是否保留由 `filter_3zi.py` 决定。
- 频次信息在当前流水线中不参与打分，仅用于抽取词条本身。
