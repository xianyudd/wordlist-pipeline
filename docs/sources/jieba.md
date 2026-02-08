# jieba

## 基本信息

- `name`: `jieba`
- `type`: `git`
- `source`: `https://github.com/fxsjy/jieba.git`

## 下载方式

由 `scripts/download.sh` 执行：

```bash
git clone --depth=1 https://github.com/fxsjy/jieba.git data/raw/jieba
```

## 原始数据格式

优先读取词典文件：

- `data/raw/jieba/jieba/dict.txt`
- 其次尝试 `dict.txt.big` 等候选路径

常见行格式：

```text
词语 词频 词性
```

## 抽取规则

`scripts/extract.py` 在 `extract_jieba()` 中：

- 对每一行按空白切分
- 取第一列作为词条

抽取结果写入：

- `data/stage1_extracted/jieba.txt`

## 注意事项

- jieba 词典覆盖广，合并后对总词量贡献较大。
- 繁简混杂、词性字段等信息在当前流程不保留，仅保留词条文本。
