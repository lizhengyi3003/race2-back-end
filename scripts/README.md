# 脚本与资料索引

在后端仓库根目录执行脚本。依赖使用 `requirements-dev.txt`；调查数据和 SQL 备份属于本地资料，不纳入 Git。

## 当前指标维护

- `migrate_202610_region_tags.py`：既有数据库的幂等区域标签结构迁移；先备份，再在目标环境运行。
- `import_indicators.py --check-only`：只解析当前 15 列源文件，核对数量和编码，不写数据库。去掉 `--check-only` 会替换现有指标配置，需预先保存人工维护的评分参数。
- `stats_indicator_config.py` / `stats_indicator_source.py`：只读统计配置覆盖率和数据来源，默认连接本地 race3 MySQL。
- `smoke_expert_engine.py`：本地专家引擎场景打印，参考分数来自旧版快照，仅作人工对照；正式回归使用 `python -m pytest tests -q`。

## 历史全国化复现

`nationalize_scan.py`、`nationalize_apply.py` 和 `verify_nationalize.py` 记录早期 3020 条、14 列指标的全国化过程。扫描及转换默认读取 `docs_archive_20260920/` 的原始版本，不操作当前前台 15 列源文件。

`nationalize_apply.py` 会在归档目录生成 `_national` 文件并更新 `data/nationalize_changes.csv`。`verify_nationalize.py`、`compare_scoring_config.py` 和 `compare_legacy_dump.py` 需要未入库的本地 SQL 备份，并只读对照数据库；其中「全部为全国」的核验口径仅适用于旧版。历史报告与当前版本的区别见归档目录 README。

## 数据与论文辅助

- `fusion/README.md`：CFPS / CHFS / CMES 多源清洗、融合与评分卡训练流程。
- `inspect_datasets.py`：只读盘点本仓库 `data/数据集/` 中的 Stata 压缩数据。
- `read_docx.py`：使用 Python 标准库提取 DOCX 文本，可按标题、关键词或段落范围查看。
- `gen_chapter3_diagrams.py`：生成第三章架构图与操作流程图，输出到 `docs/第三章配图/`；需安装开发依赖中的 matplotlib。

`data/requirements-venv-snapshot.txt` 是历史本地环境快照，供复现参考；日常安装以 `requirements.txt` 和 `requirements-dev.txt` 为准。
