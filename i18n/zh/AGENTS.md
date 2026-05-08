# llm-wiki — 运行时规范

> 个人研究 wiki，由 Codex 维护。
> 本文件是 wiki 的运行入口：定义页面结构、链接约定和工作流约束。
> 工作流改编自 OmegaWiki，PDF 预处理层已替换为 MinerU。

> **维护说明**：本文件由 `i18n/` 管理。请编辑 `i18n/zh/AGENTS.md`，不要直接编辑仓库根目录的激活副本。运行 `./setup.sh --lang zh` 同步。

---

## 仓库布局

只有需要完整目录树时才打开 `docs/runtime-directory-structure.en.md`。

请优先记住这张心智地图：

### `wiki/` 是主要产品界面

- `wiki/index.md` 是所有 wiki 页面的目录
- `wiki/log.md` 是只追加的活动日志
- `wiki/papers/` 存放论文总结
- `wiki/concepts/`、`wiki/topics/`、`wiki/foundations/` 存放可复用知识结构
- `wiki/people/`、`wiki/ideas/`、`wiki/experiments/`、`wiki/claims/` 存放研究者、假设、实验和断言
- `wiki/Summary/` 存放领域级综合
- `wiki/outputs/` 存放生成产物
- `wiki/graph/` 是派生状态，不要手动编辑

### 格式守卫

- 起草或修复 wiki 页面结构、YAML、正文区段前，先打开 `docs/runtime-page-templates.en.md`
- 需要可复制的页面起始模板时，使用 `docs/templates/`；根目录不放模板库
- 需要 graph 派生文件、`index.md` 或 `log.md` 细节时，打开 `docs/runtime-support-files.en.md`
- `SKILL.md` 是每个 skill 的即时入口；大型 skill 可能还会在自身目录下提供按需参考文件
- `/init` 是这个模式的第一个具体例子：先读 `skills/init/SKILL.md`，需要时再打开 `skills/init/references/*`

### `raw/` 和 `config/`

- `raw/papers/`、`raw/notes/`、`raw/web/` 是用户拥有的输入
- `wiki/sources/papers/` 存放 MinerU 转化后的论文 markdown（PDF 原件仍留在 `raw/papers/`）
- `wiki/sources/notes/`、`wiki/sources/web/` 存放复制到 vault 中的 notes 和 web markdown/text
- `config/` 存放环境模板（`.env.example`、`settings.local.json.example`、`paths.json.example`）
- `config/paths.json` 可用绝对路径连接外部 wiki vault 和 raw source 目录；这是本机私有配置，不提交

---

## 9 种页面类型

`papers`、`concepts`、`topics`、`people`、`ideas`、`experiments`、`claims`、`Summary`、`foundations`。

页面模板见 `docs/runtime-page-templates.en.md`；graph、index、log 参考见 `docs/runtime-support-files.en.md`。

### 论文分析分类规范

每个 `papers/{slug}.md` 必须先完成研究类型和研究对象分类：

- `paper_type`：标记文献形态，使用 `paper`、`review`、`book`、`degree_thesis`、`preprint`、`report`、`chapter`、`dataset`、`other` 之一。注意这和 `research_modes` 不同：综述论文应写 `paper_type: review`，但 `research_modes` 仍按其分析/综合的证据类型选择。
- `research_modes`：从 `theory`、`computation`、`experiment` 中选择一个或多个。综述论文按其分析/综合的证据类型选择，不要只写 `review`。
- `theory_tags`：列出使用、比较或检验的具体理论、模型、机制或分析框架。
- `computation_tags`：列出采用的计算/模拟/统计/机器学习/数据分析方案；没有则为空列表。
- `experiment_tags`：列出观测、实验、样品分析、仪器、任务或实验流程；没有则为空列表。
- `research_object_tags`：列出研究对象，例如材料、天体、系统、样品、人群、模型对象或数据集。

论文正文必须包含 `## Research classification`，分别说明：属于理论/计算/实验中的哪些方向；每个方向具体用了什么理论、计算方案或实验流程；研究对象是什么。无法从文献中确定时写 `unclear`，不要编造。

### 概念页原文溯源规范

每个 `concepts/{slug}.md` 页面必须在 `## Definition` 后包含 `## Source excerpts`。

- 对每篇实质支撑该概念的论文，加入一条简短的原文片段。
- 每条片段必须用普通 markdown 链接指向 MinerU 转化后的 markdown，通常是 `wiki/sources/papers/{paper-slug}.md`。
- 片段必须保持原文语言和原文措辞，简短引用，不要在 blockquote 中改写。
- 如果转化后的 markdown 缺失，写 `prepared markdown: missing`，并说明使用了哪个 fallback source。

示例：

```markdown
- [[paper-slug]] ([prepared markdown](../sources/papers/paper-slug.md)):
  > short exact source fragment
```

---

## 链接语法

所有内部链接都使用 Obsidian wikilink：

```markdown
[[slug]]                    ← 链接到本 wiki 中任意页面
[[lora-low-rank-adaptation]] ← 链接到 papers/lora-low-rank-adaptation.md
[[flash-attention]]          ← 链接到 concepts/flash-attention.md
```

**命名约定**：全小写、连字符分隔、无空格。

---

## 交叉引用规则

写入正向链接时，**必须同时写入反向链接**：

| 正向动作 | 必需反向动作 |
|----------|--------------|
| papers/A 写 `Related: [[concept-B]]` | concepts/B 追加 A 到 `key_papers` |
| papers/A 写 `[[researcher-C]]` | people/C 追加 A 到 `Key papers` |
| papers/A 写 `supports: [[claim-D]]` | claims/D 追加 `{source: A, type: supports}` 到 `evidence` |
| topics/T 写 `key_people: [[person-D]]` | people/D 追加 T 到 `Research areas` |
| concepts/K 写 `key_papers: [[paper-E]]` | papers/E 追加 K 到 `Related` |
| concepts/K 写 part_of `[[topic-F]]` | topics/F 在 overview 段落追加 K |
| ideas/I 写 `origin_gaps: [[claim-C]]` | claims/C 追加 I 到 `## Linked ideas` |
| experiments/E 写 `target_claim: [[claim-C]]` | claims/C 追加 `{source: E, type: tested_by}` 到 `evidence` |
| claims/C 写 `source_papers: [[paper-P]]` | papers/P 追加 C 到 `## Related` |
| 任意页面链接到 `[[foundation-X]]` | **不写反向链接**。foundations 是终端节点：可被论文/概念等指向，但不写 `key_papers` 或反向字段 |

---

## Graph 规则

- `graph/` 自动生成，不要手动编辑
- 核心派生文件是 `edges.jsonl`、`citations.jsonl`、`context_brief.md`、`open_questions.md`
- 语义边类型包括 paper-paper（`same_problem_as`、`similar_method_to`、`complementary_to`、`builds_on`、`compares_against`、`improves_on`、`challenges`、`surveys`）、paper-concept（`introduces_concept`、`uses_concept`、`extends_concept`、`critiques_concept`），以及 claim/experiment/provenance 类型（`supports`、`contradicts`、`tested_by`、`invalidates`、`addresses_gap`、`derived_from`、`inspired_by`）
- `/ingest` 写入 paper-paper 和 paper-concept 语义边时必须包含 `confidence: high|medium|low`
- 对称 paper-paper 边只存一次，端点排序，并设置 `symmetric: true`
- 文献引用存放在 `citations.jsonl`，类型为 `type: cites`
- 使用 `tools/research_wiki.py add-edge`、`add-citation`、`rebuild-context-brief`、`rebuild-open-questions`

## log.md 格式

标准日志行：

```markdown
## [YYYY-MM-DD] skill | details
```

---

## Python 环境

- 本项目由 **uv 管理**：`setup.sh` 通过 `uv sync` 从 `pyproject.toml` 创建/更新 `.venv`
- `.venv/` 存在时优先使用 `.venv/bin/python`（Unix/macOS）或 `.venv/Scripts/python.exe`（Windows）
- 否则回退到 `python3`（Unix/macOS）或 `python`（Windows）
- skill 通常按 `"$PYTHON_BIN" tools/<name>.py …` 运行工具；等价写法是 `uv run --python .venv/bin/python python tools/<name>.py …`
- Python 工具通过 `tools/_env.py` 自动加载 API key：先读进程环境，再读 `~/.config/llm-wiki/.env`（或 `$XDG_CONFIG_HOME/llm-wiki/.env`）；项目根目录 `.env` 和 `~/.env` 只是 legacy fallback
- 路径配置通过 `config/paths.json`（或环境变量 `LLM_WIKI_WIKI_ROOT`、`LLM_WIKI_RAW_ROOT`）指定外部 `wiki_root` / `raw_root`；未配置时回退到仓库内 `wiki/` 和 `raw/`
- 可选 MinerU 本地后端需显式启用：`uv sync --extra local`（首次会下载数 GB 模型权重）

---

## 约束

- **`raw/papers/`、`raw/notes/`、`raw/web/` 属于用户**：把它们视为权威输入。`/init` 和本地 `/ingest` 只可在 `wiki/sources/` 下添加 vault 可见 source 副本：PDF 只能转化为 `wiki/sources/papers/*.md`，不要把 PDF 放入 `wiki/`；notes/web 可复制到 `wiki/sources/notes/` 和 `wiki/sources/web/`。`/edit` 只有在用户明确要求时才可添加 raw source。`/init` 子代理在 INIT MODE 下仍将 `raw/` 视为严格只读，并直接消费传入的 canonical path。
- **用户可见 skill 参数属于用户**：`argument-hint` 中显示的 flag 和值属于用户命令，不是 agent 策略。不要仅凭仓库状态发明、翻转或删除这些参数。若用户省略某参数，只有 skill 文档明确说明可默认/推导时才推导，否则保持未设置或询问用户。
- **INIT MODE 交接由 manifest 驱动**：当 `/init` 写入 `.checkpoints/init-sources.json` 后，该 manifest 是 ingest 顺序和 canonical source path 的唯一事实来源。预处理后的本地输入应指向 `wiki/sources/papers/<slug>.md`。
- **graph/ 自动生成**：不要手动编辑 `graph/`，只能通过 `tools/research_wiki.py`。
- **双向链接**：写正向链接时必须同时写反向链接。
- **mineru-md 是 canonical ingest 格式**：PDF 由 MinerU（`tools/_mineru.py`）预处理为带 frontmatter 的结构化 markdown（`sections`、`figures`）。`/ingest` 和 `/init` 消费 `wiki/sources/papers/<slug>.md`，不要直接消费原始 PDF。
- **每次 ingest 都更新 index.md**；`log.md` 只追加。
- **lint 默认只报告**：`--fix` 只自动修复确定性问题（xref backlinks、缺失字段默认值）；`--suggest` 输出非确定性建议；`--fix --dry-run` 预览修复。
- **Slug 生成规则**：论文标题关键词，用连字符连接，全小写。
- **重要性评分**：1 = 小众，2 = 有用，3 = 领域标准，4 = 有影响力，5 = 开创性。
- **失败 idea 必须记录原因**：`failure_reason` 是反重复记忆，防止重复探索已知死路。
- **Claim confidence 范围**：0.0-1.0；每次 evidence 变化都重新评估。
- **Experiment 必须链接到 claim**：每个 experiment 都需要 `target_claim`；用户外部运行实验并通过 `/exp-eval` 报告结果后，把结果写回 claim evidence。
- **MinerU API token**：`MINERU_API_TOKEN` 环境变量驱动默认云端后端。没有它 PDF ingest 会失败；离线可安装本地后端（`uv sync --extra local`）。
- **文献检索**：`tools/fetch_literature.py` 使用无需 API key 的 Crossref 搜索和元数据检索。由于公开源暴露的 citation graph 较少，引用图覆盖是 best-effort。
- **仓库和 wiki 可分离**：使用 `tools/separate_wiki_repository.py` 将 `wiki/`、`raw/` 复制/移动到外部绝对路径并写入 `config/paths.json`；使用 `tools/clean_wiki_repository.py` 清理仓库内残留的 `wiki/`、`raw/`。清理脚本默认 dry-run，只有 `--yes` 才会删除。

---

## Skills

| Skill | 文件 | 触发 |
|-------|------|------|
| `/setup` | `skills/setup/SKILL.md` | 手动（首次配置） |
| `/reset` | `skills/reset/SKILL.md` | 手动（`--scope wiki\|raw\|log\|checkpoints\|all`） |
| `/init` | `skills/init/SKILL.md` | 手动 |
| `/prefill` | `skills/prefill/SKILL.md` | 手动（`[domain] [--add concept]`） |
| `/ingest` | `skills/ingest/SKILL.md` | 手动 |
| `/reingest` | `skills/reingest/SKILL.md` | 手动（重生成已有论文页） |
| `/discover` | `skills/discover/SKILL.md` | 手动 / 内部调用（由 `/ingest --discover` 调用） |
| `/ask` | `skills/ask/SKILL.md` | 手动 |
| `/edit` | `skills/edit/SKILL.md` | 手动 |
| `/check` | `skills/check/SKILL.md` | 双周 / 手动 |
| `/novelty` | `skills/novelty/SKILL.md` | 手动 |
| `/review` | `skills/review/SKILL.md` | 手动 |
| `/ideate` | `skills/ideate/SKILL.md` | 手动 |
| `/exp-design` | `skills/exp-design/SKILL.md` | 手动 |
| `/exp-eval` | `skills/exp-eval/SKILL.md` | 手动 |
| `/refine` | `skills/refine/SKILL.md` | 手动 |
| `/paper-plan` | `skills/paper-plan/SKILL.md` | 手动 |
| `/paper-draft` | `skills/paper-draft/SKILL.md` | 手动 |
| `/survey` | `skills/survey/SKILL.md` | 手动 |
| `/research` | `skills/research/SKILL.md` | 手动（仅设计型 orchestrator） |
| `/rebuttal` | `skills/rebuttal/SKILL.md` | 手动 |
