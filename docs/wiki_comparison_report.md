# 三个 Wiki 生成结果对比分析报告

**报告日期**：2026-05-09
**分析对象**：`wiki/`、`wiki_glm/`、`wiki_back/`（同一目录下由三个不同 LLM 生成）
**评判基准**：
1. 作为知识参考文献的内容质量
2. 与 `llm-wiki.md`（LLM Wiki 设计模式）的契合度

---

## 一、基本情况

### 1.1 输入差异

三份 wiki 并非完全等同条件，需要先剥离这一层：

| Wiki | 摄入源数 | 领域覆盖 |
|------|---------|---------|
| `wiki` | 1（Grant 2007 Ch.6） | 单域：原子物理 |
| `wiki_glm` | 1（Grant 2007 Ch.6） | 单域：原子物理 |
| `wiki_back` | 2（Grant 2007 + Teske 2024 综述） | 跨域：原子物理 + 系外行星 |

`wiki_back` 多摄入一篇，部分覆盖优势源于此，分析时尽量按"单源摄入触发的连锁更新"等比指标对照。

### 1.2 文件分布

| 类别 | wiki | wiki_glm | wiki_back |
|------|------|----------|-----------|
| papers | 1 | 1 | 2 |
| concepts | 3 | 3 | 3 |
| claims | 2 | **0**（空目录） | 2 |
| people | 1 | 1 | 2 |
| sources/papers | 1 | 1 | 2 |
| graph（自动聚合） | ❌ | 2 | 2 |
| log.md | ❌ | 1 行 | **3 行** |
| index.md | 人类可读 markdown | 纯 YAML | 半 YAML 半 markdown |
| 占位脚手架目录 | 无 | Summary/topics/ideas/experiments/outputs/foundations | Summary/topics/ideas/experiments/outputs/foundations |
| 资源图片本地化 | 3 张 | 3 张 | 10 张 |

---

## 二、维度一：内容质量评估

### 2.1 概念页深度对比（以 `dirac-hartree-fock` 为例）

| 项目 | wiki | wiki_glm | wiki_back |
|------|------|----------|-----------|
| 行数 | 80 | 53 | 67 |
| 数学公式 | **完整 LaTeX**（DHF energy functional、积微分方程） | ASCII 伪代码 | 仅文字描述 |
| Source excerpts | **3 段含原文 LaTeX 公式** | 1 段文字 | 1 段单句 |
| Comparison 表 | ✅ 5 行特征对比 | ❌ | ❌ |
| When to use | ✅ 给出 Z≳30 阈值 | ❌ | ✅ 较泛 |
| Variants 数量 | 5 | 3 | 4 |
| Open problems | ✅ 具体 | ❌ | ✅ 较泛 |
| My understanding | ✅ | ❌ | ✅ |

**关键观察**：`wiki` 在 `breit-interaction.md` 等概念页中保留了 Coulomb gauge / Feynman gauge 的多重原文引用、$(Z\alpha)^2$ 量级估计、Gaunt/Møller/Breit/transverse-photon 五行横向对比表 —— 这是其他两份完全缺失的。

### 2.2 论断（Claims）质量

- `wiki`：2 条 claim，confidence **0.95 / 0.90**，evidence 段含具体推理（"magnetic exchange interaction does not vanish even for closed shells"），并明确写出 counter-evidence
- `wiki_back`：2 条 claim，confidence **0.78 / 0.72**（更保守诚实），但 evidence 段较抽象
- `wiki_glm`：**没有 claims** —— claims/ 目录为空，违反知识体系最基本的一环

### 2.3 论文页（papers/complex-atoms.md）

- `wiki`：87 行，Method 拆 7 步，Results 6 条具体技术成果（cfp 表 j=3/2,5/2,7/2），引用 Grant & Pyper 1976 表号
- `wiki_glm`：107 行，章节级别拆 10 步（直接对应原文 6.1–6.10），最系统地映射原文结构
- `wiki_back`：100 行，Method/Results 写得最抽象

### 2.4 内容质量小结

| 模型 | 数学严谨性 | 引文密度 | Claims 完整 | 可读性 |
|------|-----------|----------|-------------|--------|
| **wiki** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **wiki_back** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **wiki_glm** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |

**单纯论"做出来的页面好不好读" → `wiki/` 最佳。**

---

## 三、维度二：与 llm-wiki.md 设计模式的契合度

`llm-wiki.md` 强调 wiki 是"**a persistent, compounding artifact**"，关键是**可累积、可运维、跨次会话保持一致**。这与单页质量是不同的评估维度。

### 3.1 Spec 关键要素逐项对照

| 维度 | wiki | wiki_glm | wiki_back |
|------|------|----------|-----------|
| **三层架构（raw / wiki / schema）** | ⚠️ 部分 | ✅ | ✅ 最完整 |
| **wiki 层结构丰富度** | papers/concepts/claims/people/sources | + graph + 6 空架 | **+ graph + 全脚手架** |
| **单源摄入触及多页（spec 目标 10–15）** | 8 页 | 7 页（无 claims） | **11 页（最接近）** |
| **index.md 人类可读** | ✅ **唯一带"## Papers"等 H2 标题** | ❌ 纯 YAML | ⚠️ 半 markdown |
| **log.md 存在 + 可 grep（spec 明确要求）** | ❌ **缺失** | ✅ 1 行 | ✅ **3 行格式合规** |
| **`grep "^## \[" log.md`** 可用 | ❌ | ✅ | ✅ |
| **claims 作为独立页（lint 检查项）** | ✅ | ❌ **空目录** | ✅ |
| **counter-evidence / 矛盾追踪** | ✅ 显式段落 | ❌ | ✅ |
| **graph 视图自动聚合（gap map）** | ❌ | ✅ context_brief + open_questions | ✅ |
| **Dataview-friendly YAML frontmatter** | 完整 | 完整 | **最丰富**（含 research_modes / Zotero key） |
| **跨领域累积能力验证** | 未验证（单域） | 未验证 | ✅ 已验证（双域） |

### 3.2 三者各自最贴合 spec 的部分

#### `wiki/` —— 像最终成品样张，但工厂没建
- **优势**：index.md 是唯一让人类愿意打开的；claims 段闭环（statement → evidence → counter-evidence → open questions）；source excerpts 保留原文 LaTeX 公式
- **致命缺陷**：**没有 log.md**，违反 spec 中"log gives you a timeline of the wiki's evolution and helps the LLM understand what's been done recently"
- **未来风险**：当源文献加到 5+ 篇时，没有 log/graph 的承接结构会先于其他两份遇到压力

#### `wiki_back/` —— 工厂建得最完整
- **优势**：13 个顶层目录覆盖 Summary/foundations/topics/ideas/experiments/outputs，把 spec 提到的所有扩展面"留好了位"
- **log.md 三条 init+ingest 完全符合 `^## \[YYYY-MM-DD\] type | …` 格式**，可被 spec 推荐的 `grep "^## \[" log.md | tail -5` 直接消费
- 单次 ingest 触及 11 页，是三者中最接近 spec "10–15 pages per ingest" 目标的
- graph/open_questions.md 是 lint 操作的天然产物
- 跨两个领域的摄入证明了 wiki 累积/合并能力

#### `wiki_glm/` —— 架子搭起来了，但内容留白严重
- **优势**：有 graph/ 自动聚合，log.md 格式正确
- **致命缺陷**：claims/、Summary/、ideas/、experiments/、outputs/、topics/ **全是空目录**；`index.md` 是纯 YAML，对人类不友好
- **本质问题**：spec 中"compounding artifact"的承诺没兑现，而 claims 整层缺失违反了 lint 健康检查最基本的一条

### 3.3 Spec 契合度小结

| 模型 | 内容深度 | 架构完整 | Index/Log 合规 | 跨领域累积 | spec 复合度 |
|------|---------|---------|---------------|-----------|------------|
| **wiki_back** | 中 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | **⭐⭐⭐⭐⭐** |
| **wiki** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐（缺 log） | 未验证 | ⭐⭐⭐⭐ |
| **wiki_glm** | ⭐⭐ | ⭐⭐⭐⭐（空架） | ⭐⭐⭐⭐ | 未验证 | ⭐⭐ |

---

## 四、综合结论

### 4.1 两个维度的结论分裂

- **维度一（内容质量作为参考文献）** → **`wiki/` 最佳**
- **维度二（与 llm-wiki.md 设计模式契合度）** → **`wiki_back/` 最佳**

这种分裂揭示了一个本质问题：llm-wiki 强调的不是单页好不好读，而是"**作为可持续运维的、跨域累积的、可被 lint/grep/Dataview 程序化处理的知识系统**"。`wiki_back` 命中这个 spec 的几乎全部要点；`wiki` 命中的是"读者打开后的体验"。

### 4.2 三个模型的画像

| 模型 | 画像 | 最适合的场景 |
|------|------|------------|
| **wiki** | 写出了一页好用的资料，但忘了它要被持续维护 | 单次性深度笔记、个人查阅 |
| **wiki_back** | 像一个真的在运行的系统，但内容稀薄 | 长期累积的研究 wiki，源文献会持续增加 |
| **wiki_glm** | 把架子搭好但没填东西 | 反例：搭骨架 ≠ 建知识 |

### 4.3 最佳实践建议

**以 `wiki_back/` 的工厂结构 + `wiki/` 的内容深度做并集**。具体落地：

1. **保留 `wiki_back/` 的目录契约**：
   - 保留 Summary/foundations/topics/ideas/experiments/outputs 等占位
   - 保留 log.md 的 `## [date] type | …` 格式
   - 保留 graph/context_brief.md 和 graph/open_questions.md 的自动聚合
   - 保留完整 YAML frontmatter（research_modes、domain 等）

2. **灌入 `wiki/` 的内容标准**：
   - 概念页必须有 LaTeX 公式的 source excerpts（≥2 段）
   - 概念页必须有 Comparison 表（横向对比同族物体）
   - claims 必须有 counter-evidence 段、open questions 段
   - 论文页 Method/Results 拆细到具体技术成果

3. **在 schema（CLAUDE.md / AGENTS.md）中固化以下规则**：
   - 每次 ingest 必须更新 log.md
   - 每次 ingest 必须触及 ≥8 页（向 spec 的 10–15 靠拢）
   - claims 必须配备 confidence + counter-evidence + conditions 三段
   - graph 文件由 lint 流程自动重生成

### 4.4 单选推荐

如果只能保留一份继续生长：**保留 `wiki_back/`**。

理由是 wiki 的本质是"**会一直加东西**"——架构和运维管线决定了它能不能继续生长。`wiki_back` 的内容洼地可以靠后续 ingest 和重写填补；但 `wiki` 缺失的 log、graph、占位脚手架，要么需要重做一遍架构、要么会在源文献增加时显形为系统性问题。

`wiki_glm` 不建议作为基线 —— 空目录和不可读 index 比"什么都没有"更具误导性。

---

## 附录：评估方法

- **覆盖范围**：基于 `find … -name "*.md"` 的目录树扫描
- **内容深度**：抽样阅读各 wiki 共同的概念页（dirac-hartree-fock、breit-interaction）和论文页（complex-atoms），按 LaTeX/引文/对比表/可追溯性等维度比较
- **spec 契合度**：基于 `llm-wiki.md` 文档第 25–49 行的 Architecture / Operations / Indexing 章节列出的明确要素逐项核对
- **格式合规性**：用 `grep "^## \["` 等 spec 推荐工具实测可解析性
