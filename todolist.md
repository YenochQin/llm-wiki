# Literature todo: radial-orbital-optimization candidate elements

Date: 2026-06-13

Seed idea: `radial-orbital-optimization-neutral-open-atoms`

Purpose: find literature for additional computationally meaningful elements beyond Fe I and Ni I, especially Cr/Ti/Co/Mn open-$3d$ systems and heavier Gd/Re open-shell systems.

Discovery checkpoints:
- `.checkpoints/discover-neutral-chromium-titanium-cobalt-manganese-open--2026-06-13.json`
- `.checkpoints/discover-neutral-transition-metal-atoms-cr-i-ti-i-co-i-mn-2026-06-13.json`
- `.checkpoints/discover-neutral-gadolinium-rhenium-heavy-open-shell-atom-2026-06-13.json`
- `.checkpoints/discover-10-1086-519987-2026-06-13.json`
- `.checkpoints/discover-10-1139-cjp-2016-0689-2026-06-13.json`
- `.checkpoints/discover-10-1103-physreva-107-l051102-2026-06-13.json`
- `.checkpoints/discover-10-1016-j-sab-2022-106590-2026-06-13.json`

## Priority candidates

| Priority | Element direction | Candidate | DOI | Zotero | Why it matters |
|---:|---|---|---|---|---|
| 1 | Cr I | Experimental branching fractions, transition probabilities and oscillator strengths in Cr I | `10.1016/j.jqsrt.2021.107880` | not collected | Modern Cr I BF/$gf$ benchmark; strongest immediate addition for open-$3d$ neutral comparison with Fe I / Ni I. |
| 2 | Cr I | Radiative lifetimes in Cr I by laser induced fluorescence | `10.1016/S0022-4073(97)00028-9` | not collected | Lifetime foundation for Cr I transition probabilities; pairs naturally with BF measurements. |
| 3 | Cr I | Laser spectroscopy of the y 7P_J^o states of Cr I | `10.1103/PhysRevA.105.032812` | not collected | Cr I level/spectroscopy information for open-$3d$ structure; useful for defining target states. |
| 4 | Sm I / open-$4f$ | Multiconfiguration Dirac-Hartree-Fock calculations of excitation energies, oscillator strengths, and hyperfine structure constants for low-lying levels of Sm I | `10.1103/PhysRevA.92.052505` | not collected | Direct neutral lanthanide MCDHF computation; useful method analogue before moving to Gd I. |
| 5 | Fe II benchmark | The FERRUM project: experimental lifetimes of highly excited Fe II 3d6 4p levels and transition probabilities | `10.1088/0953-4075/32/24/306` | not collected | Fe-group BF+LIF benchmark workflow; not neutral, but useful for transition-data validation standards. |
| 6 | Fe II benchmark | The FERRUM Project: Experimental transition probabilities of [Fe II] and astrophysical applications | `10.1051/0004-6361:20021557` | not collected | Forbidden/weak-line benchmark for open-$3d$ ions; relevant to gauge and cancellation diagnostics. |
| 7 | Ti II benchmark | The FERRUM Project: experimentally determined metastable lifetimes and transition probabilities for forbidden [Ti II] lines observed in eta Carinae | `10.1111/j.1365-2966.2005.09157.x` | not collected | Ti open-$3d$ benchmark; supports Ti as a candidate element even though the paper is ionized Ti. |
| 8 | Ti/Cr applications | Laser cooling of transition-metal atoms | `10.1103/PhysRevA.102.053327` | not collected | Application and experimental-operability context for transition-metal atoms such as Ti and Cr. |
| 9 | Re I | Hyperfine structure and isotope shift studies of rhenium by laser optogalvanic spectroscopy | `10.1007/BF02875383` | not collected | Older Re I HFS/IS chain that complements `[[liu_2023_Hyperfine]]`; useful for heavy open-$5d$ validation. |
| 10 | Re II / application | Atomic data for the Re II UV 1 multiplet and the rhenium abundance in the HgMn-type star chi Lupi | `10.1086/303539` | not collected | Re atomic-data application; motivates heavy open-$5d$ calculations. |
| 11 | Re I | Isotope shifts for the 5d56s7s and 5d56s6d configurations of Re I | `10.1007/BF01426878` | not collected | Direct Re I isotope-shift benchmark for heavy open-$5d$ atomic structure. |
| 12 | Dy I / Dy II | Atomic transition probabilities for Dy I and Dy II | `10.1016/S0022-4073(99)00173-9` | not collected | High-citation lanthanide transition-probability benchmark; useful comparison for Gd I / open-$4f$ expansion. |

## Background candidates

| Candidate | DOI | Zotero | Why it matters |
|---|---|---|---|
| Cowan, R. D. 1981, The Theory of Atomic Structure and Spectra | `10.1525/9780520906150` | collected | HFR / semi-empirical radial-parameter baseline for comparing against MCDHF. |
| New Light on Stellar Abundance Analyses: Departures from LTE and Homogeneity | `10.1146/annurev.astro.42.053102.134001` | not collected | NLTE background for interpreting neutral Fe-group line benchmarks. |
| On inelastic hydrogen atom collisions in stellar atmospheres | `10.1051/0004-6361/201116745` | not collected | Collision/NLTE background for Fe-group neutral species. |
| Hyperfine anomaly in heavy atoms and its role in precision atomic searches for new physics | `10.1103/PhysRevA.104.022823` | not collected | Heavy-element HFS uncertainty context, relevant for Re/Gd-style targets. |

## Low-priority or noisy hits

Do not ingest for this idea unless a separate reason appears:
- Withdrawn transition-metal DFT preprints from Research Square.
- Generic La/Sm/Tm/Tb branching-fraction papers unless the project explicitly expands to lanthanide benchmark surveys.
- Highly charged-ion transition-rate papers such as Sc XIX, Co XVI, Xe XI; useful elsewhere, but not central to neutral open-shell radial-orbital optimization.
- Broad astronomy / clock-network background from the Ti anchor unless needed for introduction motivation.

## Suggested ingest order

1. `/ingest --doi 10.1016/j.jqsrt.2021.107880`
2. `/ingest --doi 10.1016/S0022-4073(97)00028-9`
3. `/ingest --doi 10.1103/PhysRevA.105.032812`
4. `/ingest --doi 10.1103/PhysRevA.92.052505`
