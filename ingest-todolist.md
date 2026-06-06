# Ingest Todolist

待入库文献，按优先级排列。每项标注关联 claim / 核心价值。

---

## P1 — 直接量化支撑，优先处理

### Wang, Jönsson et al. 2018 — ApJS 235, 27

- **标题**: Energy Levels, Lifetimes and Transition Rates for P-like Ions from Cr X to Zn XVI from Large-Scale Relativistic Multiconfiguration Calculations
- **作者**: Wang K., Jönsson P., Gaigalas G., Radžiūtė L., Rynkun P., Del Zanna G., Chen C. Y.
- **期刊**: The Astrophysical Journal Supplement Series, 235, 27 (2018)
- **DOI**: 10.3847/1538-4365/aab315
- **arXiv**: 1802.09671
- **关联 claim**: [[mcdhf-subpercent-energy-medium-z]]
- **核心价值**: 覆盖 Z=24（Cr）到 Z=30（Zn）精确 medium-Z 范围；Fe XII（Z=26）最低 41 个能级与 NIST 能量均方差仅 **0.057%**，是当前最直接的 Claim 3 定量支撑。

---

### Jönsson et al. 2016 — A&A 585, A26

- **标题**: Accurate multiconfiguration calculations of energy levels, lifetimes, and transition rates for the silicon isoelectronic sequence: Ti IX – Ge XIX, Sr XXV, Zr XXVII, Mo XXIX
- **作者**: Jönsson P., Radžiūtė L., Gaigalas G., Godefroid M., Marques J. P., Brage T., Froese Fischer C., Grant I. P.
- **期刊**: Astronomy & Astrophysics, 585, A26 (2016)
- **DOI**: 10.1051/0004-6361/201527106
- 10.1051/0004-6361/201628768
- **关联 claim**: [[mcdhf-subpercent-energy-medium-z]]
- **核心价值**: Si-like 等电子序列 Z=22–32（Ti–Ge），能级精度 **0.01–0.03%**，跃迁率强线 dT < 1%；跨 Z 范围最宽的 medium-Z 精度基准之一。

---

## P2 — 支撑 Claim 2（Dirac-Coulomb 必要性），补充对比数据

### Gustafsson et al. 2017 — A&A 597, A76

- **标题**: MCDHF and RCI calculations of energy levels, lifetimes and transition rates for 3l3l′, 3l4l′, and 3s5l states in Ca IX – As XXII and Kr XXV
- **作者**: Gustafsson S., Jönsson P., Froese Fischer C., Grant I. P.
- **期刊**: Astronomy & Astrophysics, 597, A76 (2017)
- **DOI**: 10.1051/0004-6361/201628768
- **关联 claim**: [[dirac-coulomb-mandatory-above-z35]], [[mcdhf-subpercent-energy-medium-z]]
- **核心价值**: Mg-like Ca IX–As XXII（Z=20–33）及 Kr XXV（Z=36），直接对比 MCDHF/RCI 与 MCHF-Breit-Pauli 结果；Z=26–36 跨越 Claim 2 的阈值区间，提供 MCHF-BP 何时开始偏离的实证数据。

---

## P3 — 历史基准，补充 Claim 1 & 2 的序列对比

### Froese Fischer, Tachiev & Irimia 2006 — ADNDT 92, 607–812

- **标题**: Relativistic energy levels, lifetimes, and transition probabilities for the sodium-like to argon-like sequences
- **作者**: Froese Fischer C., Tachiev G., Irimia A.
- **期刊**: Atomic Data and Nuclear Data Tables, 92, 607 (2006)
- **DOI**: 10.1016/j.adt.2006.03.001
- **关联 claim**: [[breit-qed-necessary-above-z30]], [[dirac-coulomb-mandatory-above-z35]]
- **核心价值**: Na-like 到 Ar-like 序列（跨越 Z≈26–30 转变区间），同时提供 MCHF-Breit-Pauli 和 MCDHF 结果；是 froesefischer_2023_Atomic 中 Z≲30 阈值陈述的原始数据来源之一。优先级低于前两项，因阈值已由 froesefischer_2023_Atomic 覆盖。

---

## 备注

- P1 两篇优先通过 Zotero 检索（`/zotero-collection-list` 或手动搜索），确认 PDF 可用后 `/ingest`
- P2、P3 若 Zotero 无收录，可先 `/ingest-light` 作为背景文献，待需要时升级
- 三篇 claim（`breit-qed-necessary-above-z30`、`dirac-coulomb-mandatory-above-z35`、`mcdhf-subpercent-energy-medium-z`）的 confidence 在 P1/P2 入库后应重新评估
