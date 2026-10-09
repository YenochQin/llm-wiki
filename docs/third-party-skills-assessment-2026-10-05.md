# 第三方科研技能评估：K-Dense 与 ARS-Codex

评估日期：2026-10-05。用途：决定后续安装范围与位置。本次只下载、读取和检查源码结构，没有安装技能、启用插件、执行第三方脚本或安装科学计算依赖。

## 结论

针对现有 llm-wiki，优先引入 K-Dense 的少量计算与绘图技能，增量价值更直接；针对独立论文项目，ARS-Codex 更适合提供统一的写作、评审、修订和流程状态管理。两者可以互补，暂不需要二选一，也没有实测依据判定哪一个在论文质量上全面更优。

建议保留当前两个源码副本，把安装作为独立的后续步骤：K-Dense 按技能选择，ARS 按完整套件选择。暂不整体接入 llm-wiki 的运行入口。

## 源码快照与检查范围

| 项目 | K-Dense | ARS-Codex |
|---|---|---|
| 仓库 | `K-Dense-AI/scientific-agent-skills` | `Imbad0202/academic-research-skills-codex` |
| 本地路径 | `third_party/skill-sources/scientific-agent-skills/` | `third_party/skill-sources/academic-research-skills-codex/` |
| 包版本 | `2.72.0`，来自根 `plugin.json` | `3.23.0`，来自套件入口元数据 |
| Commit | `154988403bb5a18e9d3c0ce4e6d5e2e4b184a298` | `52228e8280dd1770e18ecfc3b1fdf16b13b58104` |
| 最近提交日期 | 2026-10-01 | 2026-10-04 |
| 可安装入口 | 177 个独立的 `skills/*/SKILL.md` | 1 个 `academic-research-suite`，内部路由到 6 个工作流 |
| 本地下载方式 | `git clone --depth 1` | `git clone --depth 1` |

检查了全部 178 个顶层技能入口的 YAML，均可解析且具有非空字符串 `name` 和 `description`；两个包之间未发现重复的顶层技能名称。此项不等于完整 Agent Skills 规范认证。

K-Dense 的 177 个入口均不超过 500 行，121 个技能目录含有顶层 Python 辅助脚本。ARS 的路由入口为 595 行；套件内部包含 2,637 个文件，其中 484 个 Python 文件、247 个 `test_*.py` 文件。结构不同，不能用脚本数或测试文件数直接给质量排名。

ARS 的 `skills/academic-research-suite/` 与 `plugins/ars-codex/skills/academic-research-suite/` 文件集合和文件内容完全一致，可以选择技能安装或插件安装其中一种。不要重复安装两份。

重点阅读了 K-Dense 的科学写作、文献综述、评审、引文管理、统计分析和科学可视化入口，以及 ARS 的 Codex 路由、完整流水线、实验工作流和运行策略。其余领域技能只进行了目录与元数据盘点，未逐项核实 API、版本或数值方法。

## 按任务比较

| 需求 | 更合适的选择 | 判断依据与限制 |
|---|---|---|
| 用具体 Python 库计算、分析或绘图 | K-Dense | 有按库与任务分开的入口，例如 `sympy`、`matplotlib`、`pymc`、`qutip`。需要逐项验证依赖与物理/统计假设。 |
| 单个独立任务，如绘图、文献元数据整理 | K-Dense | 可只安装少量专门技能，避免引入整个论文流程。 |
| 论文研究、写作、评审、修订连续衔接 | ARS | 一个路由入口组织多个工作流，使用 Material Passport 等持久状态和完整性检查。 |
| 多阶段论文流程的决策记录与恢复 | ARS | 有阶段、交接、恢复和审核记录契约；相应资料准备与维护成本更高。 |
| 维护现有 wiki 页面与知识图谱 | llm-wiki 自有技能 | 两个库均不能直接替代本仓库的页面模板、双向链接、Evidence Pack 和 grounding gate。 |
| 能否提高实际论文质量 | 尚未判断 | 未在相同输入、模型和评价标准下进行比较试验。文档和结构检查不能证明效果优劣。 |

K-Dense 的科学写作也有明确的证据绑定和本地一致性检查，并非只有通用写作提示。其当前入口要求由人工打开并核实支持来源，再将其标记为已验证。使用这个技能时，不能把 llm-wiki 已生成的 Evidence Pack 自动视为完成了它的人工核实要求。

ARS 并不要求所有任务都跑完整流水线：明确的写作、评审或引文任务可直接进入相应模式。它的适配器保留当前用户/运行时模型选择；安装技能不会自动改变当前会话模型。

## 与 llm-wiki 的衔接问题

### 1. 两套证据结构需要明确映射

llm-wiki 使用规范化 Evidence Pack、`[[#^E1]]` 块链接、canonical MinerU markdown，以及 paper/concept/claim 页面关系。K-Dense 写作使用自己的来源清单、claim CSV 和标记；ARS 使用 Material Passport、Claim Registry 等结构。

在两个库的技能代码和文档中搜索 `grounding_lint`、`evidence_pack`、`key_papers`、`rebuild-context-brief`、`MinerU` 和 `mineru`，未发现命中。这支持“没有现成的本仓库适配”这一判断，但不是对所有潜在兼容方式的否定。

后续接入时，外部技能可以消费 wiki 输出的材料，写回 wiki 仍应走现有模板、反向链接和 grounding gate。外部套件检查通过，不能替代 wiki 检查。

### 2. 完整流水线包含作者决策节点

ARS 上游 `academic-pipeline/WORKFLOW.md` 写有阶段结束后确认再继续的规则；Codex 路由同时要求复用既有授权，并明确“展示检查点本身不是新的许可请求”。因此，不能简单断言它每一步都会重新询问，也不能假定它能跳过实际作者决策、评审标准或外部服务授权节点。

对日常局部任务，优先使用明确的单一模式。只有确实需要阶段记录和完整流程时，才选择完整流水线。

### 3. 实验执行边界不同

llm-wiki 的 `/research` 是设计型工作流，实验由用户在外部执行后返回结果。ARS 的 `experiment-agent` 含 `run` 模式，可执行用户提供的实验命令，但自身禁止自动生成或修改实验脚本、自动重试崩溃实验。

在 llm-wiki 中继续保持现有设计与评估边界。需要执行实验时，在论文项目内明确选择任务和工作目录。

### 4. 技能安装与依赖安装应分开

K-Dense 文档明确解释多个科学计算库存在依赖版本冲突，推荐按技能隔离环境。安装技能目录不意味着应把所有 Python 包装入 llm-wiki 的 `.venv`。本次没有验证入口中声明的版本是否在本机可安装。

ARS 的固定运行拓扑、hooks 和外部模型路径属于可选功能；普通套件安装不需要一并启用。当前 `agents/openai.yaml` 允许隐式调用，因此用户级安装后会扩大它匹配研究、写作、评审任务的范围。

## 后续安装建议

### 第一批候选

| 技能 | 建议 | 原因 |
|---|---|---|
| K-Dense `matplotlib` | 优先候选 | 面向具体绘图 API 和输出控制，可补充现有论文图表工作。 |
| K-Dense `scientific-visualization` | 优先候选 | 多面板、单位、不确定性、缺失值、颜色和导出检查，与 `matplotlib` 的 API 指导互补。 |
| K-Dense `sympy` | 有符号推导需求时安装 | 支持精确代数、显式假设和 LaTeX 输出。 |
| K-Dense `statistical-analysis` / `pymc` | 有相应数据分析任务时安装 | 统计检验与贝叶斯建模各有依赖；不能把全部计算结果都当成抽样统计问题。 |
| K-Dense `qutip` | 有量子动力学任务时安装 | 主要处理闭合与开放量子系统动力学，不应由名称推断为通用原子结构计算工具。 |
| ARS `academic-research-suite` | 论文项目内试用 | 保留完整套件目录，从一个明确的写作或修订模式开始。 |

暂缓把 K-Dense 的 `scientific-writing`、`literature-review`、`peer-review` 和 ARS 一起全局启用。它们与已有工作流在触发范围上重叠，应先确定每类任务的主入口。

### 安装位置

1. 源码保留在本仓库 `third_party/skill-sources/`，用于比较、读取与固定版本。该目录已加入 `.gitignore`。
2. 最初可在 `/Users/yiqin/Documents/paper_project/.agents/skills/` 安装候选技能，限定试用范围。尚未检查该项目自身的运行规则，安装前应读取其适用说明。
3. 真正在不同项目重复使用的 K-Dense 技能，可再安装到用户级 `/Users/yiqin/.agents/skills/`。当前内置安装器默认目的地是 `~/.codex/skills/`；应明确选定一种位置，避免重复副本。
4. 不将第三方技能直接混入 llm-wiki 的 `skills/` 或 `i18n/*/skills/`，也不修改其运行入口来自动加载这些套件。

项目与用户级发现路径参见 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。后续安装应固定上表 commit，并保留每个技能的脚本、参考文件和资产，而不只复制 `SKILL.md`。

## 如果要进一步判断实际效果

用同一组已准备的来源、同一模型、相同输出约束分别评估一个固定任务。建议优先比较已有论文段落的证据核对与修订，而不是开放式生成整篇论文。

记录：事实与数字是否忠实、引用支持是否正确、修订是否解决指定问题、过程需要多少人工决策、总耗时与可见工具调用。K-Dense 与 ARS 的结果都应接受相同标准检查；若写回 wiki，再运行 llm-wiki 的 grounding gate。

本次没有执行这种对比，因此“更合适”是依据结构与任务匹配的判断，不是实测质量排名。

## 主要本地依据

- [K-Dense 仓库规范](../third_party/skill-sources/scientific-agent-skills/AGENTS.md)
- [K-Dense 科学写作](../third_party/skill-sources/scientific-agent-skills/skills/scientific-writing/SKILL.md)
- [K-Dense 科学可视化](../third_party/skill-sources/scientific-agent-skills/skills/scientific-visualization/SKILL.md)
- [K-Dense 文献综述](../third_party/skill-sources/scientific-agent-skills/skills/literature-review/SKILL.md)
- [K-Dense 评审](../third_party/skill-sources/scientific-agent-skills/skills/peer-review/SKILL.md)
- [K-Dense 引文管理](../third_party/skill-sources/scientific-agent-skills/skills/citation-management/SKILL.md)
- [K-Dense 统计分析](../third_party/skill-sources/scientific-agent-skills/skills/statistical-analysis/SKILL.md)
- [ARS Codex 入口与运行适配](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/SKILL.md)
- [ARS 完整流水线](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/academic-pipeline/WORKFLOW.md)
- [ARS 实验工作流](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/experiment-agent/WORKFLOW.md)
- [ARS 隐式调用策略](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/agents/openai.yaml)
