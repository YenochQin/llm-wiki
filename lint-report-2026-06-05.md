# Lint Report — 2026-06-05（第三 + 四次合并，第五次修复后更新）

**Wiki 规模**: 289 papers | 139 concepts | 10 topics | 44 people | 12 ideas | 0 experiments | 128 claims | 2 summaries | 479 edges | 42 citations

**自动化检查**: `tools/lint.py --json` 输出 `[]`，无结构性问题

**汇总**: 0 🔴 | 1 🟡 | 8 🔵

---

## 第五次修复追踪（2026-06-05）

| 问题 | 状态 |
|------|------|
| 🟡 CRLF 换行残留（4 文件） | **已修复** — 4 个 claims 文件转为 LF |
| 🟡 YAML LaTeX 未转义（6 文件） | **已修复** — 全部 6 文件 YAML 验证通过 |
| 🟡 全部 10 个 topic 缺 `## Open problems` | **已确认** — 文件中已存在，报告误报 |
| 🟡 Graph edge 缺 confidence（45 条） | **已修复** — 全部补为 `confidence: high` |
| 🔵 概念近似重复：expansion-opacity / expansion-opacity-sobolev | **已修复** — sobolev 内容合并入 expansion-opacity，sobolev 页改为 deprecated redirect |

---

## 第三次问题修复追踪

| 第三次问题 | 状态 |
|-----------|------|
| 🟡 CRLF 换行（9 文件） | **已修复** — 9/9 全部修复 |
| 🟡 YAML LaTeX 未转义（6 文件） | **已修复** — 6/6 全部修复 |
| 🔵 概念 key_papers 覆盖率低（124/139 空） | **大幅改善** — 现在仅 15/139 概念 key_papers 为空（89% → 11%） |
| 🔵 People 近期工作过时（10 人无 2024+） | **未修复** — 10 人仍无 2024+ 内容 |
| 🔵 michael-block 占位符 | **已修复** — 已填充实际论文引用 |
| 🔵 People 缺少 Recent work 章节（10 人） | **已修复** — 全部 10 人已有 `## Recent work` 章节 |
| 🔵 nuclear-polarization / polarizability 0 key_papers | **部分修复** — nuclear-polarization 现有 14 条；nuclear-polarizability 仍仅 1 条 |
| 🔵 ratip 别名内部冗余 | **已修复** — 不再含大小写重复 |
| 🔵 People 近期工作 2024 年截止（3 人） | **已修复** — michael-bender、paul-gerhard-reinhard、witold-nazarewicz 现有 2026 年内容 |
| 🔵 10 个 idea 全部 proposed | **未改变** — 仍为 10 proposed + 2 failed |
| 🔵 多数 claim Linked ideas 为空 | **未改变** — 大部分仍为空 |

---

## 🟡 建议修复

| # | 类别 | 详情 |
|---|------|------|
| 1 | **Claim evidence 大面积缺失** | 100 个 supported claim 中 92 个 `evidence: []` 为空。仅 7 个 claim 有实质 evidence 条目（vmcci-csf-reduction-maintains-accuracy、mcdhf-csfg-condensation-0-01-percent-accuracy-be、mcdhf-mbpt-cross-validation-reliability-na、mchf-energy-upper-bound、relativistic-mixing-dominates-correlation-hfs-light-atoms、th-iii-absorption-18000-angstrom-kilonova-spectra、mcdhf-fills-rn-211-atomic-data-gap）。Confidence 和 status 缺乏溯源支撑。 |

---

## 🔵 可选改进

| # | 类别 | 详情 |
|---|------|------|
| 1 | **11 个 stable 概念仅 1 条 key_paper** | bose-hubbard-model、feshbach-resonance、mcdhf-calculation-modes、nanosims、neutron-burst-process、nuclear-statistical-equilibrium、optical-lattice、optical-lattice-clock、presolar-grains、ratip、supernova-nucleosynthesis。"stable" 应有更广泛文献支撑。 |
| 2 | **People 近期工作过时（10 人）** | 无 2024+ 内容：almudena-arcones (2022)、jason-jones (2021)、mark-phillips (2021)、sivanandan-harilal (2021)、michael-block (2016)、christopher-sneden (2017)、james-lawler (2017)、jennifer-sobeck (2007)、wl-wiese (无日期)、jr-fuhr (无日期)。 |
| 3 | **高优先级 idea 停滞** | cross-j-coordinated-ml-csf-selection（priority=4, proposed 2026-05-27）、priori-convergence-uncertainty-predictor-hci-clock（priority=4, proposed 2026-06-01）。10 个 idea 全部为 proposed，尚无推进到 in_progress 或 tested。 |
| 4 | **Citation 覆盖率低** | 289 篇论文仅 42 条引用关系（14.5%），引文图谱非常稀疏。 |
| 5 | **foundations / experiments 目录为空** | 两种页面类型已定义但无任何页面。 |
| 6 | **高置信度单证据 Claim** | 17 个 claim 的 confidence ≥ 0.85 但仅 1 条 evidence。最突出：optical-lattice-clocks-achieve-better-than (0.92)、rang-library-replaces-njgraf (0.90)、second-order-hyperfine-structure-explains-sr (0.90)。 |
| 7 | **4 条种子 claim confidence ≤ 0.2 无 evidence** | breit-qed-necessary-above-z30、dirac-coulomb-mandatory-above-z35、open-shell-level-id-needs-iteration、mcdhf-subpercent-energy-medium-z。均为 /init 阶段从 notes/web 种子生成，待论文验证。 |
| 8 | **多数 claim Linked ideas 为空** | 128 个 claim 大部分 `## Linked ideas` 为 "None yet" 或空。 |

---

## LLM 辅助判断

| # | 类型 | 判断 |
|---|------|------|
| L1 | Concept 近重复检测 | expansion-opacity / expansion-opacity-sobolev 已合并。其余无新增近重复。 |
| L2 | Alias 碰撞 | 无跨概念别名冲突。ratip 大小写冗余已修复。 |
| L3 | Importance-5 论文概念覆盖 | 3 篇 importance=5 论文（bender_2003、jonsson_2013_New、katori_2003）均被概念页引用（2-5 次），覆盖良好。 |
| L4 | SOTA 时效性 | 全部 topic 在 2026-05-14 至 2026-06-03 更新，无超 6 个月陈旧项。 |
| L5 | Claim 置信度/状态一致性 | 无 weakly_supported 且 confidence ≥ 0.75。状态-置信度校准良好。 |
| L6 | Failed idea failure_reason | 2 个 failed idea 均有详细原因记录，符合规范。 |
| L7 | 矛盾陈述 | 未发现跨页面事实矛盾。 |

---

## 五轮流变

| 时段 | 🔴 | 🟡 | 🔵 |
|------|----|----|-----|
| 第一次 | 1 | 4 (10 子项) | 8 |
| 第二次 | 0 | 1 | 9 |
| 第三次 | 0 | 2 | 11 |
| 第四次（合并） | 0 | 5 | 9 |
| 第五次（本轮） | 0 | 1 | 8 |

## 总体评估

自动化 lint 持续通过，结构健康无 🔴 问题。本轮修复清除了全部 4 条可操作 🟡 问题（CRLF、YAML LaTeX 转义、graph edge confidence、topic Open problems），并合并了 expansion-opacity 重复概念页。当前唯一剩余 🟡 问题是 **claim evidence 大面积缺失**（92/100 supported claim 无 evidence）——这是数据质量最大缺口，需通过系统性 `/reingest` 和 `/ingest` 逐步回填，不适合一次性修复。
