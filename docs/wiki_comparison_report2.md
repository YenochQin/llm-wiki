# 三个 Wiki 生成结果对比分析报告

**报告日期**：2026-05-09  
**分析对象**：`wiki/`、`wiki_glm/`、`wiki_back/`  
**参照文档**：`llm-wiki.md`  
**核心问题**：三份由不同模型生成的 wiki，哪一份更适合作为后续长期维护的 LLM Wiki 基线？

## 执行摘要

结论需要分两层看：

| 评估目标 | 最佳结果 | 说明 |
|---|---|---|
| 单篇论文/单主题内容质量 | `wiki/` | 概念页更深，公式、引文、对比表、claims 闭环更完整 |
| 与 `llm-wiki.md` 设计模式的契合度 | `wiki_back/` | 具备 log、graph、sources、脚手架和多源累积痕迹 |
| 作为长期 Obsidian LLM Wiki 继续维护 | `wiki_back/` | 架构最接近可持续运转的知识库 |
| 不建议作为主基线 | `wiki_glm/` | 有结构雏形，但 claims 缺失、index 不友好、空目录较多 |

最终建议：**以 `wiki_back/` 作为主项目骨架，吸收 `wiki/` 的内容写作标准。**

`wiki/` 像一组质量很高的研究笔记；`wiki_back/` 像一个已经开始运转的知识库系统；`wiki_glm/` 有若干正确的结构判断，但完成度不足，不适合作为主线。

## 一、评估前提

### 1.1 输入条件并不完全相同

三份 wiki 的输入范围不同，不能只按文件数量或页面数量直接比较。

| Wiki | 摄入源数 | 领域覆盖 | 比较时需要注意 |
|---|---:|---|---|
| `wiki/` | 1 | Grant 2007 Ch.6，原子物理 | 单源、单域，适合看单篇生成质量 |
| `wiki_glm/` | 1 | Grant 2007 Ch.6，原子物理 | 单源、单域，适合与 `wiki/` 直接对照 |
| `wiki_back/` | 2 | Grant 2007 + Teske 2024 | 多源、跨域，适合看长期累积能力 |

`wiki_back/` 多摄入了一篇系外行星综述，因此它在页面数量、log 数量和跨域结构上的优势不完全来自模型质量。比较时应把它视为“长期 wiki 形态样本”，而不是与另外两份完全等价的单源输出。

### 1.2 文件结构概览

| 类别 | `wiki/` | `wiki_glm/` | `wiki_back/` |
|---|---:|---:|---:|
| papers | 1 | 1 | 2 |
| concepts | 3 | 3 | 3 |
| claims | 2 | 0 | 2 |
| people | 1 | 1 | 2 |
| sources/papers | 1 | 1 | 2 |
| graph 文件 | 无 | 有 | 有 |
| log.md | 无 | 1 条 ingest | init + 2 条 ingest |
| index.md | 人类可读 markdown | YAML 清单 | 半结构化 markdown/YAML |
| 空脚手架目录 | 少 | 多 | 多 |
| Obsidian 配置 | 无 | 无 | 有 |

三个目录的内部 wiki link 检查均未发现断链。差距主要不在链接可用性，而在内容深度、维护轨迹和信息架构。

## 二、内容质量比较

这里的“内容质量”指：作为研究参考材料是否好读、可信、可追溯，并且能否把论文中的关键知识拆成可复用页面。

### 2.1 概念页质量

以 `dirac-hartree-fock` 相关页面为例：

| 项目 | `wiki/` | `wiki_glm/` | `wiki_back/` |
|---|---|---|---|
| 数学表达 | 完整 LaTeX 公式 | ASCII 伪代码为主 | 文字概括为主 |
| Source excerpts | 多段，含公式 | 少量 | 少量 |
| Comparison 表 | 有 | 无 | 无 |
| When to use | 有，且给出适用阈值 | 无 | 有，但较泛 |
| Variants | 较完整 | 较简 | 中等 |
| Open problems | 具体 | 缺失或较弱 | 有，但较泛 |
| My understanding | 有 | 无 | 有 |

`wiki/` 在概念页上最像可复用的研究笔记。它不仅解释概念，还保留了公式、原文来源、横向比较和适用条件。尤其在 `breit-interaction.md` 等页面中，`wiki/` 对 Coulomb、Gaunt、Moller、Breit、transverse photon 等相关概念的区分更细。

`wiki_glm/` 的优势在于抓住了 `quasispin-seniority` 这个关键概念，这是 `wiki/` 没有单独拆出的节点。但它的概念页正文更像概要，不如 `wiki/` 适合直接作为参考材料。

`wiki_back/` 的概念页更稳健、保守，但抽象程度偏高，技术细节和原文可追溯性弱于 `wiki/`。

### 2.2 Claims 层质量

| 项目 | `wiki/` | `wiki_glm/` | `wiki_back/` |
|---|---|---|---|
| claims 页面 | 有 2 条 | 无 | 有 2 条 |
| confidence | 偏高 | 无 | 更保守 |
| evidence | 较具体 | 无 | 较抽象 |
| conditions/scope | 有 | 无 | 有 |
| counter-evidence | 有 | 无 | 有 |
| open questions | 有 | 无 | 有 |

`wiki/` 的 claims 层最完整，能够形成 statement、evidence、conditions、counter-evidence、open questions 的闭环。不过它的 confidence 数值偏高，部分表述如“necessary and sufficient”略强，后续可以调低或改写得更谨慎。

`wiki_back/` 的 claims 更保守，confidence 更像真实研究判断，但 evidence 颗粒度不如 `wiki/`。

`wiki_glm/` 缺少 claims 层，这是它作为知识库基线的明显短板。`llm-wiki.md` 虽然没有强制规定 claims 目录，但它强调 contradictions、claims、synthesis 和 lint；没有 claims 层会削弱长期综合能力。

### 2.3 论文页质量

| 项目 | `wiki/` | `wiki_glm/` | `wiki_back/` |
|---|---|---|---|
| 章节映射 | 中等 | 最强，对应 6.1-6.10 | 中等 |
| Method 拆分 | 具体 | 最系统 | 较抽象 |
| Results | 技术点丰富 | 技术点丰富 | 较概括 |
| Limitations/Open questions | 好 | 好 | 中等 |
| 可读性 | 好 | 中等 | 好 |

`wiki_glm/` 在论文页结构上表现最好，尤其是按原文章节 6.1-6.10 展开，适合还原论文结构。

但如果把论文页放回整个 wiki 生态看，`wiki/` 更能把论文内容转化成概念页和 claims 页；`wiki_glm/` 虽然论文页系统，但没有把这些系统性内容充分沉淀到 claims 和人类可读 index 中。

### 2.4 内容质量结论

| 排名 | Wiki | 理由 |
|---:|---|---|
| 1 | `wiki/` | 概念页最深，公式和引文最充分，claims 闭环最好 |
| 2 | `wiki_glm/` | 论文页结构映射强，抓住关键概念，但综合层缺失 |
| 3 | `wiki_back/` | 内容更保守稳健，但单篇技术深度不足 |

如果目标是“把 Grant 2007 Ch.6 做成好读、可查、可复用的研究笔记”，应优先参考 `wiki/`。

## 三、与 `llm-wiki.md` 模式的契合度

`llm-wiki.md` 的重点不是生成一组漂亮页面，而是建立一个“persistent, compounding artifact”：wiki 应该能长期摄入新来源、更新已有页面、记录历史、维护索引、暴露开放问题，并支持 Obsidian/Dataview/grep 等工具化使用。

### 3.1 关键要素对照

| 要素 | `wiki/` | `wiki_glm/` | `wiki_back/` |
|---|---|---|---|
| raw/wiki 分层 | 有 sources | 有 sources | 有 raw + sources |
| schema/规则文件 | 无 | 无 | 无 |
| index.md | 最可读 | 太像机器清单 | 可用但可读性一般 |
| log.md | 缺失 | 有，1 条 | 有，3 条 |
| grep 友好 log | 不适用 | 是 | 是 |
| graph/context | 无 | 有 | 有 |
| open_questions/gap map | 无独立聚合 | 有 | 有 |
| 多源累积 | 未验证 | 未验证 | 已体现 |
| Obsidian 友好性 | 中等 | 中等 | 最强 |
| Dataview frontmatter | 有 | 有 | 最丰富 |

`wiki_back/` 最接近 `llm-wiki.md` 设想的运行形态。它已经表现出 init、ingest、graph、open questions、sources、Obsidian 配置和跨源合并这些特征。

`wiki/` 的问题是没有 `log.md` 和 `graph/`。这意味着它更像一次性产物，而不是一个能让后续 agent 理解“最近发生了什么”的长期系统。

`wiki_glm/` 有 log 和 graph，但内容层没有跟上：claims 目录为空，index 不适合人读，许多脚手架目录没有实际沉淀。

### 3.2 三者画像

| Wiki | 画像 | 最适合场景 | 主要风险 |
|---|---|---|---|
| `wiki/` | 高质量研究笔记包 | 单次深度阅读、个人查阅 | 后续多源维护压力大 |
| `wiki_glm/` | 有图谱意识的半成品 | 作为结构参考或反例 | 空架多，综合层弱 |
| `wiki_back/` | 已开始运转的知识库系统 | 长期研究 wiki | 单页内容密度需要补强 |

### 3.3 模式契合度结论

| 排名 | Wiki | 理由 |
|---:|---|---|
| 1 | `wiki_back/` | 最像可持续维护的 LLM Wiki，具备多源累积和运维文件 |
| 2 | `wiki/` | 内容强，但缺少 log/graph 等维护机制 |
| 3 | `wiki_glm/` | 有维护文件，但内容沉淀不足 |

如果目标是“按照 `llm-wiki.md` 建一个会继续生长的 Obsidian 知识库”，应优先保留 `wiki_back/`。

## 四、与前次模型判断的差异

前次模型判断曾把 `wiki_glm/` 评为单篇论文生成效果最好，理由是它对 Grant 章节结构的映射最完整。经过与本报告对照后，这个判断需要修正：

1. `wiki_glm/` 的论文页结构确实强，但这只是内容质量的一部分。
2. `wiki/` 在概念页、source excerpts、数学表达、claims、counter-evidence 和人类可读 index 上更接近高质量研究 wiki。
3. `wiki_back/` 在单页内容深度上不如 `wiki/`，但更符合 `llm-wiki.md` 的长期系统目标。

因此，修正后的判断是：

| 维度 | 最佳 |
|---|---|
| Grant 论文内容质量 | `wiki/` |
| 原文章节结构映射 | `wiki_glm/` |
| LLM Wiki 系统契合度 | `wiki_back/` |
| 长期维护基线 | `wiki_back/` |

## 五、最终建议

### 5.1 单选结果

如果只能保留一份继续生长，选择：**`wiki_back/`**。

理由：长期 wiki 的关键瓶颈不是单页写得多漂亮，而是能否持续摄入、记录、链接、聚合、暴露问题并保持结构一致。`wiki_back/` 已经具备这些基础设施。它的内容深度不足可以通过后续 rewrite、lint 和补充 ingest 改进；而 `wiki/` 缺失的 log、graph 和运维结构，在规模变大后会成为系统性短板。

### 5.2 最佳融合方案

不要简单三选一。最优方案是：

**`wiki_back/` 的系统骨架 + `wiki/` 的内容标准 + `wiki_glm/` 的章节映射意识。**

具体执行：

1. 以 `wiki_back/` 作为主目录和后续维护对象。
2. 把 `wiki/` 中更深的概念页内容迁入 `wiki_back/` 对应页面。
3. 为 `wiki_back/` 的 Grant 相关页面补充更完整的 LaTeX、source excerpts、comparison 表和技术细节。
4. 保留 `wiki_back/` 的 `log.md`、`graph/context_brief.md`、`graph/open_questions.md` 和目录契约。
5. 从 `wiki_glm/` 吸收 `quasispin-seniority` 页面，以及按 6.1-6.10 对应原文结构的论文页组织方式。
6. 新建 schema 文件，例如 `AGENTS.md`，把 ingest、query、lint、index/log 更新规则固化下来。

### 5.3 建议固化到 schema 的规则

后续维护时，建议把以下规则写入项目 schema：

1. 每次 ingest 必须更新 `log.md`，格式使用 `## [YYYY-MM-DD] ingest | source title`。
2. 每次 ingest 必须更新 `index.md`，并提供页面链接、一句话摘要和关键元数据。
3. 每篇 paper 至少更新 paper、concept、people、claims、graph/open_questions 五类页面；若不适用，需要在 log 中说明。
4. 每个 concept 页面应包含 Definition、Source excerpts、Intuition、Formal notation、Variants、Comparison、Known limitations、Key papers。
5. 每个 claim 页面应包含 Statement、Evidence summary、Conditions and scope、Counter-evidence、Linked ideas、Open questions。
6. `graph/context_brief.md` 和 `graph/open_questions.md` 应由 lint 流程定期重生成。
7. 对 confidence 数值保持保守，避免把“基础性方法”写成过强的“充分必要”论断。

## 六、附录：评估方法

本报告基于以下检查：

1. 目录树扫描：比较 papers、concepts、claims、people、sources、graph、log 等结构。
2. 内容抽样：重点阅读 `dirac-hartree-fock`、`breit-interaction`、`complex-atoms` 等共同主题页面。
3. 结构核对：对照 `llm-wiki.md` 的 Architecture、Operations、Indexing and logging 三部分。
4. 维护性检查：检查 `log.md` 是否可 grep，graph/open questions 是否存在，index 是否适合人和 agent 共同使用。
5. 公平性修正：将 `wiki_back/` 的多源优势与另外两份单源输出区分开看。

## 七、最终结论

`wiki/` 赢在内容，`wiki_back/` 赢在系统，`wiki_glm/` 赢在部分结构意识但整体完成度不足。

用于长期项目时，选择 `wiki_back/`。  
用于内容修缮时，参考 `wiki/`。  
用于论文结构补强时，参考 `wiki_glm/`。

最终建设路线：**以 `wiki_back/` 为主线，把它修成具有 `wiki/` 内容深度的长期 LLM Wiki。**
