---
title: "Giant planet-metallicity correlation"
aliases:
  - "planet-metallicity correlation"
  - "Fischer-Valenti correlation"
  - "giant-planet [Fe/H] correlation"
tags:
  - exoplanets
  - stellar-abundances
  - planet-formation
  - host-stars
maturity: stable
key_papers:
  - "[[star-planet-composition-connection]]"
first_introduced: "Gonzalez 1997; Santos et al. 2001, 2004; Fischer & Valenti 2005"
date_updated: 2026-05-08
related_concepts: []
---

## Definition

The empirical observation that the occurrence rate of close-in gas-giant planets around FGK dwarfs increases steeply with host-star iron abundance `[Fe/H]`. Above roughly solar metallicity, the giant-planet hosting fraction is several times the rate near `[Fe/H] ≈ -0.3`; below `[Fe/H] ≈ -0.7` the occurrence becomes consistent with zero in current samples (Boley et al. 2021; the most metal-poor known hot-Jupiter host, WASP-98, sits at `[Fe/H] = -0.6 ± 0.19`).

## Source excerpts

- [[star-planet-composition-connection]] ([prepared markdown](../sources/papers/star-planet-composition-connection.md)):
  > giant planet-metallicity correlation

## Intuition

Close-in giant planets form predominantly via core accretion (Pollack et al. 1996); their formation is rate-limited by the time it takes a solid core to grow large enough to runaway-accrete gas before disk dispersal. More metals in the protoplanetary disk means more solid mass to feed core growth, so giant-planet formation efficiency rises sharply with `[Fe/H]`. In contrast, gravitational-instability formation is largely insensitive to disk metallicity, so a steep `[Fe/H]` dependence is itself evidence for the core-accretion pathway.

## Formal notation

The trend is commonly fit as a power law in metallicity, integrated over period:

```
f_planet ∝ 10^(β · [Fe/H])
```

with β ≈ 2 for short-period gas giants around FGK dwarfs (Fischer & Valenti 2005; Sousa et al. 2011; Mortier et al. 2013). Petigura et al. (2018) and Wilson et al. (2022) provide modern fits using CKS+LAMOST and APOGEE-Kepler metallicities respectively. Johnson & Li (2012) propose a metallicity floor for core accretion of `[Fe/H]_crit ≈ -1.5 + log(r/AU)`.

## Variants

- **By planet size and period**: hot Jupiters show the steepest dependence; cool Jupiters track hot Jupiters above `[Fe/H] ≈ -0.3` but may diverge below; sub-Saturns and Neptune-mass planets show weaker but still positive trends; super-Earths and rocky planets show flat or weakly negative trends, except for a clear positive trend in *hot* rocky planets.
- **Mass break-point**: for FGK dwarfs the giant-planet/host-`[Fe/H]` correlation appears to vanish above ~4-10 M_Jup (Santos et al. 2017, Schlaufman 2018), interpreted as a transition to gravitational-instability formation and used as a metallicity-independent definition of the planet-vs-brown-dwarf boundary.
- **Around evolved stars and M dwarfs**: trends are noisier and partly debated; samples are smaller and stellar-evolution effects on photospheric `[Fe/H]` complicate inferences.
- **Beyond Fe**: at low `[Fe/H]` (≲ -0.3), `[X/Fe]` for α-elements (Mg, Al, Si, Sc, Ti) is enhanced in planet hosts vs. non-hosts (Brugamyer et al. 2011, Adibekyan et al. 2012), suggesting α-elements can substitute for Fe as planet-formation seeds.

## Comparison

Closely related observational trends, all of which the Teske 2024 review treats together but which the wiki keeps as bullets here rather than separate pages until more papers ground them:

- **Eccentricity-metallicity link** (Dawson & Murray-Clay 2013): metal-rich hosts show wider giant-planet eccentricity distributions, consistent with planet-planet scattering. Yee & Winn (2023) find no period-distribution difference for transiting hot Jupiters, qualifying the picture.
- **Cold-Jupiter / inner-small-planet co-occurrence**: cold Jupiters appear ~3× more frequently in systems also hosting inner small planets, with the boost concentrated above `[Fe/H] ≈ 0.1` (Zhu & Wu 2018, Bryan et al. 2019, Herman et al. 2019).
- **Compact-multiplanet vs. metallicity**: Brewer et al. (2018) and Zhu (2019) find compact multiplanet systems concentrated at moderate `[Fe/H]` and disrupted by giants at the high end.

## When to use

- as the default prior for whether an observed FGK star is likely to host a close-in giant;
- as evidence for core accretion as the dominant formation pathway for short-period gas giants below ~10 M_Jup;
- to motivate metal-poor / halo-star searches as a way to probe the lower formation floor and test planet-formation theory near the limits.

## Known limitations

- Sample-selection biases (RV programs target bright, inactive, often metal-rich stars) inflate the inferred slope unless detection limits are modeled.
- The `[Fe/H]` axis correlates with stellar mass and age, which themselves affect disk mass and lifetime; isolating "pure" metallicity dependence requires controlling for these.
- The correlation is anchored mostly at FGK dwarfs; M-dwarf abundances are still measurement-limited, and giant-planet occurrence around M dwarfs may not follow the same pattern (e.g., Gan et al. 2023).
- "Metallicity" here is `[Fe/H]`; bulk metal mass for planet formation may track other elements (α-elements, refractories) more closely.

## Open problems

- Where exactly is the lower `[Fe/H]` cutoff for giant-planet formation? TESS halo-star occurrence-rate work (Boley et al. 2021) suggests `[Fe/H] ≳ -0.7` for hot Jupiters; longer-period giants extend somewhat lower.
- Why does the dependence weaken so sharply for sub-Saturn/Neptune-mass planets? Does pebble-accretion vs. planetesimal-accretion partition responsibility?
- Is there a real second-order dependence on `[α/Fe]` independent of `[Fe/H]`, and does it shift the `[Fe/H]` floor for stream / dwarf-galaxy origin stars?
- How does the correlation behave around M dwarfs once SDSS-V Milky Way Mapper delivers H-band abundance samples?

## Key papers

- [[star-planet-composition-connection]] — Teske 2024 review

## My understanding

The cleanest way to think about this in the wiki is as the strongest single test of core accretion that the field has accumulated: a steep, repeatedly reproduced occurrence-rate slope, an inferred upper-mass cutoff that aligns naturally with a switch to gravitational instability, and a lower-`[Fe/H]` floor that is now within reach of TESS+halo-star statistics. The right way to extend this concept page is to add focused follow-up ingests of Petigura et al. (2018), Wilson et al. (2022), Boley et al. (2021), Schlaufman (2018), and Yee & Winn (2023), each of which brings either modern occurrence statistics or a sharpened mass / period / eccentricity sub-trend.
