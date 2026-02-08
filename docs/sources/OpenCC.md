# OpenCC

## 基本信息

- `name`: `OpenCC`
- `type`: `git`
- `source`: `https://github.com/BYVoid/OpenCC.git`

## 下载方式

由 `scripts/download.sh` 执行：

```bash
git clone --depth=1 https://github.com/BYVoid/OpenCC.git data/raw/OpenCC
```

## 原始数据格式

主要读取 OpenCC 字典目录中的 `*.txt`，常见路径：

- `data/raw/OpenCC/data/dictionary/*.txt`

部分行是同义/繁简映射，常见为空白分隔的多个 token。

## 抽取规则

`scripts/extract.py` 在 `extract_opencc()` 中：

- 遍历字典文本
- 跳过注释行（`#` 开头）
- 对每行按空白分词
- 将所有 token 作为候选词条输出

抽取结果写入：

- `data/stage1_extracted/OpenCC.txt`

## 注意事项

- OpenCC 数据是“转换词典”，并非通用语料词频词库。
- 合并后可能引入大量繁体词条，最终仍会经过三字过滤和去重。
