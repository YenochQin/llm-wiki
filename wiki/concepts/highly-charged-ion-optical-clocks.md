---
title: "Highly charged ion optical clocks"
aliases:
  - "HCI optical clocks"
  - "highly charged ions for optical clocks"
  - "HCI frequency standards"
tags:
  - atomic-physics
  - optical-clocks
  - highly-charged-ions
  - frequency-metrology
maturity: emerging
key_papers:
  - "[[highly-charged-ions-optical-clocks-applications]]"
first_introduced: "Schiller 2007; Berengut, Dzuba & Flambaum 2010; Kozlov et al. 2018 review"
date_updated: 2026-05-08
related_concepts:
  - "[[quantum-logic-spectroscopy-for-hci]]"
  - "[[hci-level-crossing-clock-candidates]]"
---

## Definition

Highly charged ion optical clocks use narrow transitions in ions with large positive charge states as clock references, exploiting compact electron orbitals, strong relativistic/QED effects, and high sensitivity to fundamental constants.

## Source excerpts

- [[highly-charged-ions-optical-clocks-applications]] ([prepared markdown](../../raw/prepared/papers/highly-charged-ions-optical-clocks-applications.md)):
  > optical transitions of interest to metrology in HCI occur within the ground-state configuration

## Intuition

At first glance HCI seem unsuitable for optical clocks because their gross electronic energy scales move toward the extreme UV and x-ray. The useful trick is to find transitions inside the ground configuration, near level crossings, or between hyperfine/fine-structure states so that the frequency lands in a laser-accessible range while the compact orbitals suppress many environmental shifts.

## Formal notation

Typical clock evaluation uses fractional frequency shifts:

```text
delta f / f = magnetic + electric + motion + micromotion + collision + probe shifts
```

HCI advantages often scale with charge because orbital size decreases roughly as `1 / (Q + 1)`, suppressing polarizabilities and electric-quadrupole moments, while relativistic sensitivity coefficients can grow.

## Variants

- **Hyperfine-transition HCI clocks**: hydrogenlike ions with optical or near-optical M1 hyperfine transitions.
- **Fine-structure HCI clocks**: moderately charged ions with optical fine-structure transitions.
- **Level-crossing HCI clocks**: ions whose shell reordering creates narrow optical transitions between different configurations.
- **Intraconfiguration HCI clocks**: transitions inside configurations such as `4f^12`, often interesting for Lorentz-symmetry tests.

## Comparison

Compared with neutral-atom and singly charged-ion optical clocks, HCI clocks may offer smaller polarizability and quadrupole shifts plus stronger fundamental-constant sensitivity, but they are harder to produce, cool, identify spectroscopically, and read out.

## When to use

- when evaluating clock candidates for fundamental-constant searches;
- when a transition needs low systematic shifts and high sensitivity to relativistic effects;
- when connecting atomic-structure calculations to trapped-ion metrology;
- when considering future VUV or soft-x-ray frequency standards.

## Known limitations

- Many proposed HCI species lack enough measured atomic data for a complete uncertainty budget.
- Complex open-shell HCI are hard for atomic-structure theory.
- Direct laser cooling is often unavailable, so the clock depends on sympathetic cooling and quantum-logic readout.

## Open problems

- Identify clock species with both practical readout and superior sensitivity.
- Measure transition frequencies and lifetimes for leading candidates.
- Quantify nuclear and many-body-theory limits on high-accuracy HCI clocks.

## Key papers

- [[highly-charged-ions-optical-clocks-applications]] — 2018 Reviews of Modern Physics synthesis of HCI clocks, spectroscopy, and fundamental-physics applications.

## My understanding

HCI clocks are not merely "better clocks"; their value is the unusual combination of small environmental couplings and amplified sensitivity to the physics one wants to test.
