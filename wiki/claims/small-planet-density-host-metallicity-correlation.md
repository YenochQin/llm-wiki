---
title: "Small rocky planet bulk density correlates positively with host star metallicity"
slug: "small-planet-density-host-metallicity-correlation"
status: weakly_supported
confidence: 0.55
tags:
  - exoplanets
  - stellar-abundances
  - rocky-planets
  - planet-composition
domain: "exoplanets / astrophysics"
source_papers:
  - "[[star-planet-composition-connection]]"
evidence:
  - source: "[[star-planet-composition-connection]]"
    type: supports
    strength: moderate
    detail: "Teske 2024 review re-states the Adibekyan et al. (2021) finding that the iron mass fraction predicted from host-star abundances is positively correlated with the bulk density of R_p < 1.6 R_⊕ short-period exoplanets, and judges the trend not explained by atmospheric escape. The review qualifies the result by noting (i) Plotnykov & Valencia (2020) and Schulze et al. (2021) find planet-derived core-mass-fraction distributions wider than the star-derived ones, with individual systems inconsistent at 2σ, and (ii) the three studies use different inference / modeling approaches."
conditions: "Holds for short-period (`P ≲ a few days`) exoplanets with `R_p < 1.6 R_⊕` and well-characterized masses+radii (errors below ~25%) around FGK hosts with detailed refractory-element abundances. The strength of the correlation, and whether individual outliers (super-Mercuries, very-low-density rocky planets) violate it, is still uncertain."
date_proposed: 2026-05-07
date_updated: 2026-05-07
---

## Statement

Among small (`R_p < 1.6 R_⊕`), short-period rocky exoplanets with precise mass and radius measurements, the bulk density correlates positively with host-star metallicity — specifically with the iron mass fraction inferred from host-star photospheric abundances (Adibekyan et al. 2021, as re-stated in Teske 2024 [[star-planet-composition-connection]]). Equivalently, small planets around more metal-rich stars tend to be denser, consistent with larger iron-core mass fractions, and the correlation is not attributable to atmospheric escape from a hot, irradiated envelope.

## Evidence summary

Supporting:

- Adibekyan et al. (2021): population-wide positive correlation between disk iron mass fraction (predicted from host abundances) and planet bulk density for `R_p < 1.6 R_⊕` short-period exoplanets, with the trend surviving an atmospheric-escape control.
- Conceptual support from the "star ≡ planet" approximation, which numerous studies (Thiabaud et al. 2015, Dorn et al. 2015, Brugger et al. 2017, Wang et al. 2019) have argued holds in broad outline for refractories like Mg, Si, and Fe.

Counter-evidence and qualifications:

- Plotnykov & Valencia (2020): comparing core-mass-fraction and Fe/Mg, Fe/Si distributions derived from planet density alone vs. from host-star abundances (Hypatia catalog), the planet-derived distribution is *wider* and does not peak at the same values as the star-derived one.
- Schulze et al. (2021): in two specific systems, planet-density-derived and stellar-abundance-derived core mass fractions differ at the 2σ level — one consistent with a "super-Mercury" interpretation, one with anomalously low density.
- Hinkel & Unterborn (2018): even with the assumption holding, distinguishing significantly different rocky-planet mineralogies from current measurement precisions is not always possible.

The three studies (Adibekyan 2021, Plotnykov & Valencia 2020, Schulze 2021) use different inference and modeling pipelines, and the review explicitly flags this as a confounder.

## Conditions and scope

- Restricted to short-period rocky planets (`R_p < 1.6 R_⊕`) with mass and radius errors below ~25%.
- FGK host stars with detailed refractory-element abundances available; M-dwarf hosts are largely outside the current sample.
- "Density" is the planet bulk density inferred from radial-velocity (or TTV) mass plus transit radius; "metallicity" here is best interpreted as the *predicted iron mass fraction in the protoplanetary disk* from host-star abundances, not just `[Fe/H]`.
- Atmospheric-loss-driven density variations are explicitly subtracted; the claim concerns the residual correlation.

## Counter-evidence

- Population-wide width mismatch between planet- and star-predicted core-mass-fraction distributions (Plotnykov & Valencia 2020).
- Existence of individual systems (Schulze et al. 2021) where the star-derived prediction sits 2σ from the planet-derived value, including likely super-Mercuries that no current formation model explains cleanly (collisions alone do not suffice; Scora et al. 2020).
- Current uncertainties on stellar abundances + small-planet masses+radii leave room for the correlation to be partially driven by selection of well-measured systems toward the metal-rich end.

## Linked ideas

(none yet)

## Open questions

- How does the correlation strength change as JWST + extreme-precision RVs bring more low-density and very-low-density rocky planets into the sample with tighter mass+radius errors?
- Does the relation hold around M-dwarf hosts once SDSS-V Milky Way Mapper / APOGEE M-dwarf abundance samples mature?
- What is the right composition-driver axis — `[Fe/H]`, predicted iron mass fraction, Mg/Si, or a multivariate refractory abundance — to use when phrasing the correlation?
- Are super-Mercuries and anomalously low-density small planets a distinct population breaking the relation, or rare scatter around it?
