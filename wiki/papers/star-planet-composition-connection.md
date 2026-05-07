---
title: "The star-planet composition connection"
slug: "star-planet-composition-connection"
arxiv: ""
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

> Author: Johanna K. Teske. Source: `raw/papers/Teske - 2024 - The star–planet composition connection.pdf` (prepared MinerU markdown at `raw/tmp/papers/star-planet-composition-connection.md`). `importance` is provisional — Semantic Scholar enrichment was unavailable at ingest time (rate-limited; no API key set).

## Problem

How does the elemental composition of host stars constrain the formation, presence, architecture, and bulk composition of their orbiting planets? After three decades and 5,600+ confirmed exoplanets, the field has accumulated rich abundance data but still struggles to disentangle (i) selection effects, (ii) Galactic chemical evolution (GCE) trends in `[X/Fe]`, and (iii) genuine planet-formation imprints on stellar photospheres. The review asks what stellar abundances can — and cannot — tell us under the slogan "know thy star, know thy planet".

## Key idea

The review organizes the star-planet composition connection along two axes:

1. **Stellar composition as an indicator of planet presence and architecture** — does iron metallicity (and beyond-Fe ratios) predict whether a star hosts giants, sub-Neptunes, super-Earths, or compact multiplanet systems?
2. **Stellar composition as an indicator of planet formation and composition** — once a planet exists, can host-star abundances be used as a proxy for the bulk or atmospheric composition of the planet (the so-called "star ≡ planet" assumption for rocky planets, or the C/O / refractory ratio comparisons for giants)?

A third detour treats anomalous abundance signatures — solar twins, binary pairs, and lithium — as natural laboratories for isolating planet-related processes (engulfment, depletion) from GCE and stellar mixing.

## Research classification

- **Theory**: compares core accretion, gravitational instability, Galactic chemical evolution, planet engulfment, and the rocky-planet "star ≡ planet" composition assumption.
- **Computation**: synthesizes occurrence-rate statistics, abundance-trend corrections, MESA engulfment detectability modelling, planet interior/composition inference, and population-synthesis comparisons.
- **Experiment**: reviews high-resolution stellar spectroscopy, radial-velocity and transit planet surveys, polluted white dwarf abundance measurements, and exoplanet atmosphere spectroscopy.
- **Research objects**: exoplanet host stars, FGK dwarfs, M dwarfs, giant planets, sub-Neptunes, small rocky planets, solar twins, binary stars, and polluted white dwarfs.

## Method

This is an invited review, not an original empirical study. The synthesis approach is:

- collect the major published occurrence-rate / metallicity studies (CKS, LAMOST, APOGEE-Kepler, TESS halo-star surveys, radial-velocity giant-planet samples) and re-state their consensus or disagreement;
- contrast the differential-spectroscopy literature on solar twins (Meléndez 2009 and successors) and binary pairs (16 Cyg A&B, Kronos-Krios, HIP 34407/26, etc.) on whether refractory–`T_cond` trends are explained by planet engulfment vs. GCE;
- review host-star vs. giant-planet C/O comparisons (planetesimal-accretion vs. pebble-accretion regimes, Mordasini et al. 2016, Öberg & Bergin 2016, Turrini et al. 2021);
- review the rocky-planet "star ≡ planet" assumption and its empirical tests (Plotnykov & Valencia 2020, Schulze et al. 2021, Adibekyan et al. 2021);
- summarize what polluted white dwarfs add about extrasolar planetesimal compositions (differentiation, oxidation state, ²⁶Al heating, dry-rock dominance).

## Results

Major synthesized findings:

- **The giant planet-metallicity correlation remains the strongest star-planet composition link**, with planet occurrence scaling roughly as a power-law in `[Fe/H]` with index ~2 for FGK dwarfs. Both planet mass and radius rise with host metallicity. The trend appears to break above ~4-10 M_Jup, plausibly marking a transition between core accretion and gravitational instability — and suggesting an independent definition of the planet/brown-dwarf boundary that does not depend on internal structure. See [[giant-planet-metallicity-correlation]].
- **The lower metallicity limit for giant-planet formation is constrained loosely**: radial-velocity studies and TESS halo-star searches put it near `[Fe/H] ≈ -0.7` for hot Jupiters; the most metal-poor confirmed hot Jupiter host (WASP-98) sits near that limit. At low `[Fe/H]`, α-elements may substitute for Fe as planet-formation seeds.
- **Smaller planets show a much weaker `[Fe/H]` dependence**, with hot rocky planets preferring more metal-rich stars but long-period super-Earths showing flat or slightly negative trends. The most metal-poor known small-planet host sits at `[Fe/H] ≈ -0.89`. Cold Jupiters are over-represented in systems with inner small planets, and their presence appears to suppress high-multiplicity small-planet systems.
- **Solar refractory depletion (Meléndez 2009)** as a smoking-gun for rocky-planet formation is no longer the consensus: GCE corrections, convection-zone-mass timing arguments, and follow-up samples (Bedell 2018, Nibauer 2021) show the Sun is in the more common low-contrast population; a refractory-vs-volatile signature in solar twins cannot uniquely identify planet hosts.
- **Binary-pair `T_cond` trends are mostly modest** (≲0.05 dex) and most cannot be attributed to planet engulfment specifically. Modeling with MESA (Behmard 2023a) shows engulfment is detectable mainly in older (>1.5 Gyr), >1.1 M_⊙, low-metallicity stars; quantitative estimates put genuine engulfment at ~3-8% of pairs.
- **C/O comparisons between hosts and giant planets are not a clean diagnostic** of formation location once planetesimal accretion, pebble drift, and disk C-depletion are all in play. Diversity in measured giant-planet C/O (e.g., HD 149026b ~0.80 vs. HD 209458b ~0.11) underscores the need to go beyond C/O — to S/N, refractory-to-volatile ratios, and joint atmosphere+bulk-density constraints. JWST is starting to enable this.
- **The rocky-planet "star ≡ planet" assumption is supported in broad outline but contested in detail**: Adibekyan et al. (2021) report a positive correlation between disk-iron mass fraction (predicted from host abundances) and the bulk density of `R_p < 1.6 R_⊕` planets, but Plotnykov & Valencia (2020) and Schulze et al. (2021) find the planet-derived core-mass-fraction distribution wider than the star-derived one, with individual cases inconsistent at the 2σ level (e.g., super-Mercuries). See [[small-planet-density-host-metallicity-correlation]].
- **Polluted white dwarfs** confirm that most accreted planetesimals are dry, Earth-like, oxidized, and often differentiated — implying widespread early ²⁶Al heating in extrasolar systems. Exotic exceptions (water-rich Kuiper-Belt-Object analogs, Be-enhanced bodies, evaporating icy giants) reveal compositional diversity but stay within the Solar-System range.

## Limitations

- The review is FGK-dwarf-centric; M-dwarf abundances remain measurement-limited, and the small planets that orbit M dwarfs are under-represented in every conclusion.
- Most precise abundance results are differential, anchored to the Sun; they do not necessarily generalize to stars far from solar `T_eff` and `log g`.
- Sample selection biases (transit and RV targets favor inactive, single, brighter stars) propagate into every metallicity-occurrence figure.
- Many host-vs-planet atmosphere C/O conclusions rest on a few well-characterized targets and on disk models with strong assumptions about C-depletion radii and pebble drift.
- The polluted-WD record samples planetesimals delivered by dynamical scattering, which biases what survives toward bodies that experienced specific orbital histories.

## Open questions

The review closes with five concrete prospects, which are imported here as candidate research gaps:

1. How do abundances of stars hosting Solar-System analogs (small inner + long-period giant) compare to the broader solar-twin trend, especially with Gaia DR4/DR5 long-period giants?
2. What is the genuine lower `[Fe/H]` floor for planet formation, and how do α-elements and stream/cluster origins shift it?
3. Do FGK abundance trends extend into the M-dwarf regime once SDSS-V Milky Way Mapper / APOGEE-N+S deliver large H-band M-dwarf abundance samples?
4. Where and when do giant planets form? Can JWST + ground-based high-resolution refractory + S/N detections move us beyond C/O?
5. How similar are rocky-planet refractory compositions to their host stars, leveraging "lava world" emission/phase-curve observations and large host-star abundance surveys?
6. What is the balance of oxidized vs. reduced compositions in extrasolar rocky bodies, and how does it shape habitability proxies (core size, volatile budget, mantle viscosity)?

## My take

For a wiki-of-research perspective, the most actionable takeaways:

- treat **giant-planet metallicity** as a robust prior, **small-planet density-vs-metallicity** as a promising but unsettled signal, and **solar refractory depletion** as a worked-out cautionary tale about how easy it is to misread GCE as a planet signature;
- when comparing planet atmospheres to host stars, never use a single ratio (C/O) in isolation — joint refractory + volatile + bulk-density constraints are now the bar;
- polluted white dwarfs are an underused entry point for "what do bulk planetesimal compositions look like beyond the Solar System" and should be wired into any future rocky-planet composition page.

## Related

- [[giant-planet-metallicity-correlation]] — the central host-star-composition phenomenon the review re-affirms
- [[small-planet-density-host-metallicity-correlation]] — emerging, partially supported assertion the review highlights
