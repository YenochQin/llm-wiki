---
name: cal-report-analysis
description: Use when the user wants to index wiki-local calculation outputs and write an archived analysis report from generated calculation report pages. Trigger for requests to analyze `temp/cal_data`, compare calculation runs, summarize CSV/JSONL/text/image result artifacts, or create a durable report based on `tools/cal_data_index.py` outputs.
argument-hint: "[scope] [--data-dir <dir>] [--report-dir <dir>] [--table-rows N] [--text-lines N] [--no-write]"
---

# /cal-report-analysis

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。

> 用 `tools/cal_data_index.py` 生成可在 Obsidian 浏览的 calculation report pages，然后基于这些 report pages 和它们链接的源文件写有证据支撑的分析报告。
> 适用于 configured wiki root 下的计算输出目录、实验结果 dump、metric 表、JSONL 样本、日志、配置和图像。

## Trigger

User manual: `/cal-report-analysis [scope] [...]`

当用户要求分析计算输出、比较 calculation runs、总结本地 metric/result artifacts，或基于 `temp/cal_data` 及其他 wiki-local calculation data 目录生成报告时，使用本 skill。

## Inputs

- `scope` optional：run 名称、report slug、data 子目录，或自然语言分析问题。省略时分析所有发现的 runs。
- `--data-dir` optional，默认 `temp/cal_data`：包含计算输出文件的 wiki-relative 目录。
- `--report-dir` optional，默认 `experiments/cal_reports`：indexer 写入 report pages 的 wiki-relative 目录。
- `--table-rows` optional，默认 `8`：每个 CSV/TSV 文件预览的行数。
- `--text-lines` optional，默认 `20`：每个 JSONL/text/log/config 文件预览的行数。
- `--no-write` optional：跳过归档，只在响应中返回最终分析。

## Outputs

- `experiments/cal_reports/index.md` 和每个 calculation run 的 generated report page。
- 响应中的简洁分析报告。
- 默认写入：`wiki/outputs/cal-report-analysis-{slug}-{date}.md` 和一条 log entry。
- With `--no-write`：不写入 archived analysis artifact，也不追加 log entry。

## Wiki Interaction

### Reads
- 默认读取 `temp/cal_data/`，或用户通过 `--data-dir` 指定的目录。
- 读取 indexer 生成的 `experiments/cal_reports/index.md` 和选中的 run report pages。
- 当结论依赖精确数值、完整日志或超出 preview 的图像信息时，读取 report page 链接的源文件。
- 只有当用户要求把分析连接到既有 wiki knowledge 时，才读取现有 `wiki/claims/`、`wiki/experiments/`、`wiki/ideas/` 和 `wiki/papers/`。

### Writes
- 在 `--report-dir` 下写入 generated calculation report pages；这些页面会由 indexer 重新生成，不适合作为手写 notes 的持久位置。
- 默认在 `wiki/outputs/` 下写入一个 analysis artifact。
- 默认通过 `tools/research_wiki.py log` 追加 weekly log entry。
- With `--no-write`：不写入 analysis artifact 或 log entry。

### Graph edges created
- 默认不创建。
- 如果归档分析引用了既有 wiki pages，且需要 derived provenance，则通过 `tools/research_wiki.py add-edge` 添加 `derived_from` edges。不要手动编辑 `wiki/graph/`。

## Workflow

从 llm-wiki 仓库根目录运行命令。使用 runtime path aliases，不要硬编码绝对 wiki 路径。

### Step 1: Generate or Refresh Calculation Report Pages

除非用户明确要求使用现有 report pages 不刷新，否则分析前先运行 indexer：

```shell
uv run python -X utf8 tools/cal_data_index.py @configured --data-dir temp/cal_data --report-dir experiments/cal_reports --table-rows 8 --text-lines 20
```

只有当用户提供了参数，或请求范围确实需要不同 data/report directory 时，才调整 flags。该工具会发现 direct files 和 run subdirectories，给每个 run 写一个 page，并嵌入 CSV/TSV preview、JSONL/text snippets、image links、file sizes 和 item counts。

如果命令报告 zero runs，停止并说明在 resolved data directory 下没有找到 calculation data。不要编造分析。

### Step 2: Select the Evidence Set

1. 读取 `experiments/cal_reports/index.md`。
2. 按用户 scope 选择 report pages：
   - 明确 run/report slug：读取该 page。
   - data 子目录：读取 source path 匹配的 pages。
   - comparison request：读取所有匹配的 run pages。
   - 未提供 scope：读取所有 run pages；若数量很多，先说明选择范围。
3. 对每个选中的 run，检查：
   - file inventory 和 file types。
   - row/item counts。
   - metric tables。
   - config/log snippets。
   - plots 和 image links。
4. 当 preview 不足以支持结论时，打开 linked source files，尤其是最终 metric values、完整 error traces、configuration differences 或需要视觉检查的 plots。

### Step 3: Analyze

每个 claim 都必须落到 generated report pages 或 linked source files。优先写具体 filenames 和 metric names，避免泛泛而谈。

适用时回答：

- 分析了哪些 runs，哪些文件支撑分析？
- 主要 metrics、baselines、variants 或 settings 是什么？
- 哪些 values 在 runs 之间发生了实质变化？
- 哪些 rows、samples、logs 或 plots 指向 anomalies 或 failure modes？
- 哪些 configuration differences 可能解释结果？
- 哪些结论有直接证据支持？
- 哪些问题因为 data、metadata 或 preview 不足仍未知？

不要仅凭相关性推断因果。如果 plot 或 table 暗示趋势但缺少 metadata，将其标注为 observed association。

### Step 4: Write the Analysis Report

除非用户要求其他格式，使用以下结构：

```markdown
# Calculation Report Analysis: {scope}

## Scope
- Data directory:
- Generated report index:
- Runs analyzed:
- Source files checked:

## Executive Summary

## Key Results

## Run-by-Run Notes

## Cross-Run Comparison

## Anomalies and Failure Signals

## Interpretation

## Limits and Unknowns

## Recommended Next Checks
```

保持分析具体：

- 包含 table names、column names、run names 和 linked report/source paths。
- 区分 observations 和 interpretation。
- metadata 缺失时保留不确定性。
- 避免可套用于任何实验的 generic prose。

### Step 5: Archive by Default

只有当用户提供 `--no-write` 时才跳过本步骤。

1. 根据 scope 生成 slug：

   ```shell
   uv run python -X utf8 tools/research_wiki.py slug "cal report analysis {scope}"
   ```

2. 直接写文件前先解析 configured wiki root：

   ```shell
   uv run python -X utf8 tools/resolve_path_alias.py @configured
   ```

3. 创建 `outputs/cal-report-analysis-{slug}-{date}.md`，frontmatter：

   ```yaml
   ---
   title: "Calculation Report Analysis: {scope}"
   slug: "cal-report-analysis-{slug}-{date}"
   artifact_type: cal_report_analysis
   date_created: YYYY-MM-DD
   data_dir: "{data-dir}"
   report_index: "experiments/cal_reports/index.md"
   source_reports:
     - "experiments/cal_reports/{run}.md"
   source_files:
     - "temp/cal_data/{run}/{file}"
   ---
   ```

4. 在 frontmatter 后写入 report body。
5. 如果 `wiki/index.md` 列出 outputs，则在其中添加新的 output entry。
6. 通过工具追加 log entry：

   ```shell
   uv run python -X utf8 tools/research_wiki.py log @configured "cal-report-analysis | {scope} | runs: {N} | output: outputs/{slug}.md"
   ```

7. 只有当 analysis 派生自既有 wiki pages，而不只是本地 calculation files 时，才通过 `tools/research_wiki.py add-edge` 添加 graph edges。

## Constraints

- 将 generated report pages 视为 evidence index，而非自动证明；对决定性数值或诊断 claim，要读取 linked source files。
- 将 generated report pages 视为 disposable indexer output。不要在这些页面里写持久 hand-written notes；持久解读应放入 archived analysis artifact，或放入单独的 user-authored Markdown file。
- 不要手动编辑 `wiki/graph/`。
- 除非用户明确要求 crystallization into experiment entities，不要把 report pages 转换为普通 `experiments/` pages。
- 不要覆盖用户拥有的 calculation data under `temp/cal_data/`。
- 如果文件是 binary 或 unsupported，只在 inventory 中说明，不要从文件名推断内容。
- 默认归档。只有当用户提供 `--no-write` 时，才跳过 `wiki/outputs/` 和 log 写入。

## Dependencies

### Tools
- `uv run python -X utf8 tools/cal_data_index.py @configured ...` - generate calculation report pages.
- `uv run python -X utf8 tools/research_wiki.py slug ...` - generate archive slug.
- `uv run python -X utf8 tools/research_wiki.py log @configured ...` - append log entry.
- `uv run python -X utf8 tools/research_wiki.py add-edge ...` - optional derived provenance edges.
- `uv run python -X utf8 tools/resolve_path_alias.py @configured` - resolve the active wiki root before direct writes.
