---
title: "The star-planet composition connection"
slug: "star-planet-composition-connection"
paper_type: review
venue: "Annual Review of Astronomy and Astrophysics"
year: 2024
tags:
  - exoplanets
  - stellar-abundances
  - planet-formation
  - host-stars
  - planet-composition
research_modes:
  - theory
  - computation
  - experiment
theory_tags:
  - core-accretion
  - gravitational-instability
  - galactic-chemical-evolution
  - star-planet-composition-assumption
  - planet-engulfment
computation_tags:
  - occurrence-rate-statistics
  - stellar-abundance-trend-analysis
  - mesa-engulfment-modelling
  - planet-interior-composition-inference
  - population-synthesis-comparison
experiment_tags:
  - high-resolution-stellar-spectroscopy
  - radial-velocity-surveys
  - transit-surveys
  - white-dwarf-pollution-abundance-analysis
  - exoplanet-atmosphere-spectroscopy
research_object_tags:
  - exoplanet-host-stars
  - fgk-dwarfs
  - m-dwarfs
  - giant-planets
  - small-rocky-planets
  - polluted-white-dwarfs
  - binary-stars
  - solar-twins
importance: 3
date_added: 2026-05-07
source_type: pdf
s2_id: ""
keywords:
  - exoplanets
  - stellar abundances
  - host stars
  - exoplanet compositions
  - planet formation
domain: "exoplanets / astrophysics"
code_url: ""
cited_by: []
---

> Author: Johanna K. Teske. Source: `raw/papers/Teske - 2024 - The star–planet composition connection.pdf`；prepared MinerU markdown: [wiki/sources/papers/star-planet-composition-connection.md](../sources/papers/star-planet-composition-connection.md)。`importance` 暂定为 3，因为 ingest 时外部元数据富化受限。

## Problem

这篇综述追问一个核心问题：恒星的元素丰度在多大程度上能够约束行星的存在、系统结构、形成历史和体成分？在数千颗系外行星已经被确认之后，研究者仍需要区分三类信号：观测选择效应、银河化学演化造成的丰度趋势，以及真正由行星形成或行星吞噬留下的恒星光球印记。

## Key idea

文章把“恒星-行星成分连接”拆成两条主线。第一条是把恒星丰度当作行星存在和系统结构的预测量：例如 `[Fe/H]` 是否预测巨行星、亚海王星、超级地球或紧凑多行星系统的发生率。第二条是把恒星丰度当作行星体成分的近似先验：例如岩石行星是否可以近似采用“star ≡ planet”假设，巨行星大气的 C/O 和难挥发元素比例是否能反推形成位置与吸积历史。

文章还用太阳双胞胎、双星和锂丰度异常作为自然实验，讨论吞噬行星、岩质物质亏损、恒星混合和银河化学演化如何互相混淆。

## Research classification

- **Theory**: 综述核心吸积、引力不稳定、银河化学演化、行星吞噬，以及岩石行星“star ≡ planet”成分假设。
- **Computation**: 综合行星发生率统计、恒星丰度趋势校正、MESA 行星吞噬可探测性建模、行星内部成分反演和种群合成比较。
- **Experiment**: 综述高分辨率恒星光谱、径向速度和凌星巡天、污染白矮星丰度测量，以及系外行星大气光谱。
- **Research objects**: 系外行星宿主恒星、FGK 矮星、M 矮星、巨行星、亚海王星、小型岩石行星、太阳双胞胎、双星和污染白矮星。

## Method

这是 Annual Review 综述，不是一篇新观测论文。作者按证据类型组织文献：

- 汇总 CKS、LAMOST、APOGEE-Kepler、TESS halo-star search 和径向速度巨行星样本中的金属丰度-行星发生率结果；
- 比较太阳双胞胎差分光谱和双星丰度差异研究，评估难挥发元素-凝结温度趋势到底来自行星形成、行星吞噬还是银河化学演化；
- 讨论巨行星 C/O、S/N、难挥发/挥发元素比例与形成位置、星子吸积、pebble drift 和盘内碳亏损之间的非唯一关系；
- 总结岩石行星“star ≡ planet”假设的群体检验，包括密度、核心质量分数和宿主恒星难挥发元素丰度；
- 用污染白矮星补充系外星子体成分证据，尤其是分异、氧化态、干燥程度和 `26Al` 加热。

## Results

- **巨行星-金属丰度相关仍是最强的恒星-行星成分连接。** FGK 矮星中巨行星发生率大致随 `[Fe/H]` 呈幂律上升，短周期气态巨行星最明显。这个趋势支持核心吸积是低于约 4-10 M_Jup 巨行星的主导形成通道。见 [[giant-planet-metallicity-correlation]]。
- **巨行星形成的低金属丰度下限仍不精确。** 径向速度和 TESS halo-star 搜索把 hot Jupiter 的下限大致放在 `[Fe/H] ≈ -0.7` 附近；低 `[Fe/H]` 时 alpha 元素可能替代 Fe 作为固体核心增长的关键元素。
- **小行星的 `[Fe/H]` 依赖弱得多。** 热岩石行星偏好金属更高的宿主，但长周期超级地球趋势平坦甚至略负；冷木星更常与内侧小行星共存，同时又可能压低紧凑多小行星系统的多重性。
- **太阳难挥发元素亏损不再是岩石行星形成的单一证据。** GCE 校正、对流层质量时序和后续太阳双胞胎样本都表明，难挥发-挥发元素趋势不能唯一诊断是否存在行星。
- **双星丰度差异多数较小且解释不唯一。** MESA 模型显示，吞噬行星信号主要在年龄较大、质量较高、低金属丰度的恒星中更容易被探测；真实吞噬比例估计约为几个百分点量级。
- **巨行星大气 C/O 不是干净的形成位置诊断。** 一旦考虑星子吸积、pebble drift 和盘内碳亏损，不同模型可给出相似 C/O；未来需要 S/N、难挥发元素、大气丰度和体密度联合约束。
- **岩石行星“star ≡ planet”假设在群体上有支持，但个体上有争议。** Adibekyan et al. (2021) 报告宿主丰度预测的盘铁质量分数与 `R_p < 1.6 R_⊕` 行星体密度正相关；Plotnykov & Valencia (2020) 和 Schulze et al. (2021) 则指出核心质量分数分布和若干个体系统并不完全一致。见 [[small-planet-density-host-metallicity-correlation]]。
- **污染白矮星提供了系外星子体成分窗口。** 多数被吸积的星子体看起来干燥、类地、氧化且常经历分异，暗示早期 `26Al` 加热在系外系统中可能普遍存在。

## Limitations

- 综述以 FGK 矮星为中心；M 矮星丰度测量仍受限，而 M 矮星小行星样本在结论中代表性不足。
- 高精度丰度结果多来自相对太阳的差分分析，未必能推广到远离太阳参数的恒星。
- 凌星和径向速度样本偏向明亮、安静、单星目标，选择效应会影响金属丰度-发生率关系。
- 巨行星大气成分解释依赖少数高质量目标和强模型假设。
- 污染白矮星记录的是被动力学散射后送入白矮星的物质，可能偏向特定轨道历史和幸存体类型。

## Open questions

- 太阳系类结构宿主星（内侧小行星 + 长周期巨行星）的丰度是否不同于一般太阳双胞胎？
- 行星形成真实的低 `[Fe/H]` 下限在哪里？alpha 元素、星流和星团起源如何移动这个下限？
- FGK 丰度趋势是否能扩展到 M 矮星，特别是在 SDSS-V / APOGEE M 矮星丰度成熟之后？
- JWST 和地面高分辨率光谱能否把巨行星形成诊断从 C/O 推进到难挥发元素和 S/N？
- 岩石行星难挥发元素体成分与宿主星到底有多相似？lava worlds 的相位曲线和发射光谱能否提供新检验？
- 系外岩石体的氧化/还原分布如何影响核心大小、挥发物预算和宜居性代理指标？

## My take

这篇综述最适合在 wiki 中充当“恒星丰度能告诉我们什么、不能告诉我们什么”的边界页。可靠层是 [[giant-planet-metallicity-correlation]]；有希望但仍弱支持的是 [[small-planet-density-host-metallicity-correlation]]；最重要的教训是不要把单一丰度趋势直接解释成行星形成印记，必须同时处理 GCE、选择效应、恒星演化和模型退化。

它也和 [[cosmochemistry-planetary-systems]] 互补：Teske 侧重可观测宿主星和系外行星，Bizzarro et al. 则从太阳系样品和同位素约束追踪固体物质来源。

## Related

- [[giant-planet-metallicity-correlation]] — 综述确认的最稳健宿主星成分现象。
- supports: [[small-planet-density-host-metallicity-correlation]] — 综述重点讨论但仍需限定条件的岩石行星密度-宿主丰度关系。
- [[cosmochemistry-planetary-systems]] — 互补综述，提供太阳系样品、pebble accretion 和挥发物来源视角。
