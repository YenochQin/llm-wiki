---
title: "HCI level-crossing clock candidates"
aliases:
  - "level-crossing HCI clock candidates"
  - "level crossings in highly charged ion clocks"
  - "HCI shell-crossing optical transitions"
tags:
  - atomic-physics
  - highly-charged-ions
  - optical-clocks
  - atomic-structure
  - fundamental-constant-variation
maturity: active
key_papers:
  - "[[highly-charged-ions-optical-clocks-applications]]"
first_introduced: "Berengut, Dzuba & Flambaum 2010; Kozlov et al. 2018 review"
date_updated: 2026-05-08
related_concepts:
  - "[[highly-charged-ion-optical-clocks]]"
---

## Definition

HCI level-crossing clock candidates are highly charged ions in which shell reordering along an isoelectronic sequence brings otherwise high-energy configurations close enough to create narrow optical transitions useful for clocks and tests of fundamental constants.

## Source excerpts

- [[highly-charged-ions-optical-clocks-applications]] ([prepared markdown](../sources/papers/highly-charged-ions-optical-clocks-applications.md)):
  > transitions in $\mathrm { I r ^ { 1 7 + } }$ ... have more than a factor of 20 higher sensitivity

## Intuition

As charge state increases, orbitals do not all shift at the same rate. When shells such as `4f`, `5s`, or `5p` reorder, transitions between competing configurations can accidentally land in the optical range. These transitions can be narrow, highly relativistic, and sensitive to changes in alpha.

## Formal notation

Candidate searches compare transition frequency and sensitivity:

```text
omega = E_excited(Z, Q, configuration) - E_ground(Z, Q, configuration)
K_alpha = d ln omega / d ln alpha
```

Useful candidates need laser-accessible `omega`, long lifetime, stable or long-lived isotopes, and manageable systematic shifts.

## Variants

- **Ag-like, Cd-like, In-like, Sn-like sequences**: few-valence-electron systems screened by atomic-structure calculations.
- **Actinide candidates**: Cf and related ions with high alpha sensitivity but isotope/practicality constraints.
- **Ir hole systems**: electron-hole transitions near `4f-5s` crossings with very large alpha sensitivity.
- **Intraconfiguration alternatives**: transitions within open `4f` shells when level-crossing transitions are impractical.

## Comparison

Compared with hyperfine HCI clocks, level-crossing candidates often offer higher alpha sensitivity but more complicated atomic-structure prediction and systematic-shift evaluation. Compared with fine-structure candidates, they can be narrower and more sensitive but less experimentally mapped.

## When to use

- when screening HCI for fine-structure constant variation;
- when looking for optical transitions in high-charge species;
- when connecting coupled-cluster/CI calculations to clock-candidate selection;
- when prioritizing spectroscopy targets for EBIT and cryogenic trap experiments.

## Known limitations

- Accurate transition prediction requires demanding relativistic, QED, and correlation calculations.
- Many candidate species lack measured spectra, lifetimes, polarizabilities, or quadrupole moments.
- High sensitivity can trade off against complicated state preparation and shift cancellation.

## Open problems

- Measure the leading Ir, Cf, Ag-like, In-like, and Sn-like candidate transitions.
- Improve atomic-structure calculations for multi-valence-electron HCI.
- Determine whether high alpha sensitivity can coexist with clock-grade uncertainty budgets.

## Key papers

- [[highly-charged-ions-optical-clocks-applications]] — review synthesis of level-crossing searches and candidate classes.

## My understanding

Level crossings are the atomic-structure engine behind many HCI clock proposals: they make optical transitions appear where naive charge scaling would predict only extreme-UV or x-ray structure.
