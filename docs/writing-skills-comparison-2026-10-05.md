# 写作技能比较：ARS-Codex 与 llm-wiki

评估日期：2026-10-05。比较对象是当前本地技能描述、流程和关键参考文件，没有执行写作对比试验，也没有安装或修改任何技能。

## 判断

如果选择一个通用论文写作入口，优先选 ARS-Codex 的 `academic-research-suite`，实际进入其中的 `academic-paper` 工作流。它在稿件类型、修订过程和语言编辑边界方面覆盖更完整。

如果任务是把已经整理好的 wiki 证据和 claim 转成论文计划或 Related Work，llm-wiki 的 `paper-plan`、`survey` 仍更直接。它们的优势是现有知识库衔接，而不是通用写作覆盖。

建议后续让 llm-wiki 继续负责来源整理、知识结构和证据材料，让 ARS 在独立论文项目中负责稿件组织、起草、评审和修订。暂不删除或替换本仓库现有技能。

这里的“优先”是描述与流程设计层面的适用性判断，不代表已经证明生成质量更高。

## 对照关系

`academic-research-suite` 是整个套件的路由入口，不能只用其根描述与某一个本地技能比较。对应关系如下：

| llm-wiki | ARS 对应能力 | 当前判断 |
|---|---|---|
| `paper-plan` | `academic-paper`: `outline-only` / `plan` | 已有 wiki claim 图时本地入口更直接；需要按不同学科、论文类型建构结构时 ARS 更合适。 |
| `paper-draft` | `academic-paper`: `full` | ARS 的写作配置和论文类型覆盖更完整；本地技能更贴合既有 `PAPER_PLAN` 和 LaTeX 文件组织。 |
| `survey` | `academic-paper`: `lit-review`，以及 `deep-research` 的综述工作流 | 只消费已入库文献时 `survey` 更合适；需要重新组织外部检索与研究问题时 ARS 覆盖更广。两者的综述模式也不能自动视为完整系统综述。 |
| `review` | `academic-paper-reviewer` | 本地技能适合当前 agent 的快速审查；ARS 有更细的期刊契合、方法、领域和反方角色，以及修订后复查。角色更多不等于错误独立。 |
| `refine` | `academic-paper`: `revision` + reviewer 的 `re-review` | ARS 更强调作者裁决、指定修改范围、patch 和修改核对；本地循环较简单，可直接利用 wiki 实体，但以评审分数作为停止条件。 |
| `rebuttal` | `revision-coach` / `revision` / `rebuttal-audit` | 本地技能可直接写有 wiki 证据的完整逐条回复；ARS 区分修订路线、回复骨架、原稿修订和已有回复的覆盖审查，边界更细。`rebuttal-audit` 本身不生成回复。 |
| `research` | `academic-pipeline` | 前者连通知识库和用户外部实验结果，后者强调论文各阶段交接与状态；完整流程都有资料和决策成本，不宜为局部编辑自动启动。 |

## ARS 描述与流程更好的地方

### 1. 稿件适配更完整

ARS 的 academic-paper 描述列出 11 种模式，参考模板覆盖 IMRaD、文献综述、理论文章、会议论文等不同稿件。它先确定学科、目标期刊、论文类型、已有材料、输出格式和作者需求，再组织写作。

本地 `paper-plan` 的公开参数列出的 venue 是 ICLR、NeurIPS、ICML、ACL、CVPR、IEEE。其 Step 1 将“没有任何实验结果支持 claim”定义为错误；约束部分虽写到 empirical paper，但入口没有论文类型分流，也没有明确的纯理论例外。对理论、数值计算或其他非 ML 稿件，不能假定这套入口已适配。

本地 `paper-draft` 的固定输出结构是 introduction、related_work、method、experiments、conclusion；评审提示要求模型扮演 senior ML researcher；匿名投稿约束又直接禁止作者、单位和致谢。这些都是具体的范围限制。

依据：[paper-plan](../skills/paper-plan/SKILL.md)、[paper-draft](../skills/paper-draft/SKILL.md)、[ARS academic-paper](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/academic-paper/WORKFLOW.md)。

### 2. 润色原则更注重科学含义

本地共享 writing reference 包含固定词语替换、必须去除 AI 特征以及“审稿人能否猜出由 AI 生成”等表述；draft 中还要求移除过度 hedging。共享 source-grounding 规则要求避免过度结论，可以制约这种操作，但写作入口没有把“必要限定语”和“冗余表达”的区分展开。

ARS 的 writing-quality checklist 明确定位为清晰、准确的写作诊断，并把词语、标点和结构模式作为非阻断建议，保留学科术语、引用、作者风格和结论强度。它的 claim-strength ladder 进一步禁止静默移除 `may` 等限定语，或在关联、预测和因果表述之间改动强度。

因此，在“如何润色而不改变科学含义”的描述设计上，ARS 更完整。claim ladder 仍有解释性边界：机械检查只能保护已登记并绑定的表面和数值/引用 token，不能自动检出全部语义变化。

依据：[本地写作原则](../skills/shared-references/academic-writing.md)、[本地 source-grounding](../skills/shared-references/source-grounding.md)、[ARS writing-quality checklist](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/academic-paper/references/writing_quality_check.md)、[ARS claim-strength ladder](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/shared/references/claim_strength_ladder.md)。

### 3. 修订过程更细

本地 `refine` 默认按当前评审的分数、ready verdict 或最大轮数停止。这个过程能提供实用反馈，但分数上升不是外部质量验证。本地 `review` 明确由当前 agent 完成，不自动调度独立评审。

ARS 将审稿意见、作者接受/拒绝的修改选择、实际 patch、修订后的稿件，以及回复信审查区分开。它要求保留作者决定和精确修改范围，再核对是否完成实际改动。对于已有稿件和审稿意见，这种流程设计更细，也需要更多作者决策记录。

依据：[refine](../skills/refine/SKILL.md)、[review](../skills/llm-review/SKILL.md)、[ARS draft-writer](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/academic-paper/agents/draft_writer_agent.md)、[ARS reviewer](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/academic-paper-reviewer/WORKFLOW.md)。

## 本仓库更好的地方

### 1. 明确消费已有知识库

`paper-plan` 明确读取 claim 状态、证据关系、实验结果、concept 形式化定义和 open questions，并输出 claim→evidence→section 矩阵。`survey` 可直接利用已有文献和 paper-paper 语义关系，按主题组织 Related Work。

ARS 没有本仓库的 MinerU source、Evidence Pack 块链接、双向链接或 research_wiki 图维护适配。把 wiki 页面交给 ARS，不等于自动完成这些规则；需要明确的材料交接和写回约束。

### 2. 单项任务入口清楚

本地各 description 清楚地说明输入和产物，六个技能分工容易预测。ARS 用一个较宽的 description 匹配研究、写作、引文、评审和修订，再由内部路由定位模式。这个方式减少顶层目录条目，但需要正确的模式选择。

局部任务的开销目前没有测量。从结构判断，本地 `review` 或 `survey` 更容易用于范围固定的快速工作；ARS 的完整流程则有更多配置、状态和交接产物。单次调用 ARS 的专门模式可减少这种成本。

### 3. 已有证据规则明确，但 LaTeX 检查边界必须保留

本地 shared source-grounding 明确要求先提取证据、禁止从模型记忆补数字和比较，并允许使用已溯源 wiki 页面。其 `grounding_lint.py` 只机械检查 papers、concepts、claims；LaTeX 论文和 outputs 仍依赖人工或 agent 的逐项溯源核对。

因此，本地知识库证据链是实际优势，但不能把“wiki grounding 检查通过”解释为“最终论文所有句子都已验证”。

## 当前可执行性问题

本地 writing skills 中的 `.claude/skills/shared-references/` 引用能够解析到 `i18n/en/shared-references/`，并非丢失文件。但它们仍使用 Claude 风格工具与 `mcp__llm-review__chat` 的调用描述。当前会话的可用工具目录没有这个 review MCP 工具。

`paper-plan` 将外部 Review LLM 评审写为 mandatory，同时又允许不可用时自评降级；`paper-draft` 的 `--review` 是章节评审选项，Step 5 却另写全文 cross-review。fallback 标记可以保留真实性，但外部评审承诺与具体执行边界需要澄清。

ARS 有明确的 Codex 适配入口，把上游角色提示映射到本地运行时，固定拓扑和 hooks 默认关闭。它也不是无条件更可靠：角色分离不能证明错误独立，契约不能证明模型遵循，目标期刊适配仍需要真实规则和材料。

本次只报告这些规范问题，没有修改 `skills/`、`i18n/*/skills/`、共享参考或 AGENTS。

## ARS 自身仍需注意的范围

- 默认参考语境是高等教育，引用风格包含 APA 等方案；需要指定实际学科、目标期刊和引用格式。
- 当前摘要语言对注册表只支持 `zh-tw-en`，默认传统中文/英文表面并不等于正文必须双语；单语英语稿件应明确摘要需求。
- 一些 writing-judgment 参考仍用较简单的学科声音规则，例如把物理论文里的 `We argue` 当作不合适示例。实际用语应服从目标期刊和作者材料，不能一律套用。
- 精确修订授权和多阶段完整性记录能提高可追踪性，也可能增加交互与材料准备。应按任务选专门模式，避免默认运行完整 pipeline。

依据：[ARS Codex 入口](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/SKILL.md)、[ARS writing-judgment](../third_party/skill-sources/academic-research-skills-codex/skills/academic-research-suite/ars/academic-paper/references/writing_judgment_framework.md)。

## 建议的后续使用方式

1. 文献整理和来源核查：继续用 llm-wiki 的 ingest、source-audit 等技能。
2. 已有 wiki 材料汇总：保留 survey，以及适合现有稿件类型的 paper-plan；不要绕过它当前的文档限制来假装支持其他类型。
3. 通用起草、稿件结构与修订：在 paper_project 内试用 ARS 的明确模式。
4. 写回 wiki：继续使用 llm-wiki 的页面结构、反向链接和 scoped grounding gate。
5. 真实效果判断：用同一批来源和结果、同一模型、同一段落/修订任务比较输出；评估数字、符号、限定语、引用支持和修改范围，不以模型自评分代替。

若未来要把本地写作技能改造成更通用的入口，可优先修正：论文类型分流、venue 参数、匿名要求条件化、润色时的科学含义保护，以及 Codex 工具映射。该修改需要单独任务，本次未执行。
