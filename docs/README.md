# 数据源文档

本文档目录用于说明各数据源的来源、数据特点、在本项目中的处理方式和使用注意事项。

## 数据源列表

- [THUOCL](sources/THUOCL.md)
- [jieba](sources/jieba.md)
- [OpenCC](sources/OpenCC.md)
- [zhwiki_titles_ns0_gz](sources/zhwiki_titles_ns0_gz.md)
- [hanyuguoxue_changdu3_top50](sources/hanyuguoxue_changdu3_top50.md)

## 与流水线的对应关系

- 下载/抓取：`scripts/download.sh`
- 抽取阶段：`scripts/extract.py`
- 规范化：`scripts/normalize.py`
- 三字过滤：`scripts/filter_3zi.py`
- 合并统计：`scripts/wordlist.py`

如果你新增了数据源，建议在 `docs/sources/` 增加同名文档，便于后续维护。
