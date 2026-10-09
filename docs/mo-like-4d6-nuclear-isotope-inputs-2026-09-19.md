# Mo-like $4d^6$ HCI: nuclear and isotopic inputs

**Purpose.** This note fixes a practical initial isotope set for the proposed
Mo-like HCI sequence

$$
\mathrm{Ce}^{16+},\ \mathrm{Nd}^{18+},\ \mathrm{Sm}^{20+},\ \mathrm{Gd}^{22+},\ \mathrm{Dy}^{24+},\ \mathrm{Er}^{26+},\ \mathrm{Yb}^{28+}.
$$

It supplies the requested neutral-atom masses and nuclear inputs for (i)
even-$A$, $I=0$ isotope-shift (IS) pairs and (ii) odd-$A$ hyperfine-structure
(HFS) candidates.  It does **not** substitute neutral-atom masses for the ion
mass in a bound-electron calculation; see the caveats below.

## Provenance and conventions

All numerical entries in the two data tables were retrieved on 2026-09-19 from
the IAEA Nuclear Data Services LiveChart **ground-state** API, source key
`LC(<nuclide>)`.  The exact record is reproducible by substituting the key in

<https://www-nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides={nuclide}>.

For example, `LC(143nd)` denotes the evaluated $^{143}\mathrm{Nd}$ record.
The API documentation lists the returned ground-state columns, including
`jp`, `magnetic_dipole`, `electric_quadrupole`, `atomic_mass`, abundance, and
their uncertainty fields [IAEA LiveChart API notebook](https://iaea-nds.github.io/lc_api_notebook/).
Its data model specifies that `atomic_mass` is in micro-u; values below divide
that field and its uncertainty by $10^6$ to give u
[IAEA NDLab field documentation](https://iaea-nds.github.io/ndlab/_static/ndlab-tutorial.html).

This is an evaluated-data selection, not a new nuclear evaluation.  The
underlying recommended reference families are AME2020 for masses
([Wang *et al.*, 2021](https://doi.org/10.1088/1674-1137/abddaf)), Stone's
recommended magnetic-moment compilation
([IAEA INDC(NDS)-0794](https://doi.org/10.61092/iaea.yjpc-cns6)), and Stone's
electric-quadrupole compilation
([IAEA INDC(NDS)-0833](https://doi.org/10.61092/iaea.a6te-dg7q)).  LiveChart
also exposes the ENSDF evaluation cutoff in every returned record; a production
calculation should re-query and archive the returned CSV before values are
frozen for publication.

Notation: $I^\pi$ is the ground-state spin/parity; $\mu$ is in $\mu_N$;
$Q$ is the spectroscopic electric quadrupole moment in barn; and a mass written
as $x(y)$ means $x\pm y$ in the final quoted digits.  For an $I=0$ nucleus,
$\mu=Q=0$ by angular-momentum symmetry, so the table labels these as `0
(I=0)` instead of treating an empty database moment field as missing.

## Recommended isotope roles

| Mo-like ion | $Z$ | IS baseline: natural even-$A$, $I=0$ pair | HFS baseline | Selection rationale |
|---|---:|---|---|---|
| $\mathrm{Ce}^{16+}$ | 58 | $^{140}\mathrm{Ce}/^{142}\mathrm{Ce}$ | $^{139}\mathrm{Ce}$ only if a radioactive source is feasible | The two IS isotopes are natural; Ce has no naturally occurring odd-$A$ isotope. |
| $\mathrm{Nd}^{18+}$ | 60 | $^{142}\mathrm{Nd}/^{150}\mathrm{Nd}$ | $^{143}\mathrm{Nd}$, $^{145}\mathrm{Nd}$ | Both odd isotopes are natural and have evaluated $\mu$ and $Q$. |
| $\mathrm{Sm}^{20+}$ | 62 | $^{144}\mathrm{Sm}/^{154}\mathrm{Sm}$ | $^{147}\mathrm{Sm}$, $^{149}\mathrm{Sm}$ | Natural endpoints give a broad mass span; $^{147}$Sm is extremely long-lived rather than stable. |
| $\mathrm{Gd}^{22+}$ | 64 | $^{154}\mathrm{Gd}/^{160}\mathrm{Gd}$ | $^{155}\mathrm{Gd}$, $^{157}\mathrm{Gd}$ | All four are naturally occurring. |
| $\mathrm{Dy}^{24+}$ | 66 | $^{160}\mathrm{Dy}/^{164}\mathrm{Dy}$ | $^{161}\mathrm{Dy}$, $^{163}\mathrm{Dy}$ | $^{160}$Dy is less abundant but natural; the two HFS isotopes are relatively abundant. |
| $\mathrm{Er}^{26+}$ | 68 | $^{166}\mathrm{Er}/^{170}\mathrm{Er}$ | $^{167}\mathrm{Er}$ | This avoids the much rarer $^{162}$Er while retaining a four-mass-unit IS span. |
| $\mathrm{Yb}^{28+}$ | 70 | $^{170}\mathrm{Yb}/^{176}\mathrm{Yb}$ | $^{171}\mathrm{Yb}$, $^{173}\mathrm{Yb}$ | $^{173}$Yb is the quadrupole-HFS isotope; $^{171}$Yb has $I=1/2$ and hence no $B$ term. |

The chosen IS pairs are planning baselines, not an assertion that they are the
only useful pairs.  They balance a nonzero mass/radius lever arm with
naturally occurring material.  If isotope enrichment, source loading, or
charge-breeding changes the practical constraint, neighbouring even-$A$
isotopes should be retained as alternatives rather than inferred from these
values.

## Isotope-shift inputs: even-$A$ nuclei

| Ion and isotope | $Z$ | $A$ | Neutral-atom mass (u) | $I$ ($\hbar$) | $\mu/\mu_N$ | $Q$ (b) | Natural abundance (%) | Source |
|---|---:|---:|---|---|---|---|---:|---|
| $^{140}\mathrm{Ce}^{16+}$ | 58 | 140 | 139.905448433(1409) | 0 | 0 (I=0) | 0 (I=0) | 88.449(51) | LC(140ce) |
| $^{142}\mathrm{Ce}^{16+}$ | 58 | 142 | 141.909250208(2623) | 0 | 0 (I=0) | 0 (I=0) | 11.114(51) | LC(142ce) |
| $^{142}\mathrm{Nd}^{18+}$ | 60 | 142 | 141.907728824(1348) | 0 | 0 (I=0) | 0 (I=0) | 27.153(40) | LC(142nd) |
| $^{150}\mathrm{Nd}^{18+}$ | 60 | 150 | 149.920901322(1211) | 0 | 0 (I=0) | 0 (I=0) | 5.638(28) | LC(150nd) |
| $^{144}\mathrm{Sm}^{20+}$ | 62 | 144 | 143.912006285(1566) | 0 | 0 (I=0) | 0 (I=0) | 3.08(4) | LC(144sm) |
| $^{154}\mathrm{Sm}^{20+}$ | 62 | 154 | 153.922215756(1400) | 0 | 0 (I=0) | 0 (I=0) | 22.74(14) | LC(154sm) |
| $^{154}\mathrm{Gd}^{22+}$ | 64 | 154 | 153.920872974(1066) | 0 | 0 (I=0) | 0 (I=0) | 2.18(2) | LC(154gd) |
| $^{160}\mathrm{Gd}^{22+}$ | 64 | 160 | 159.927061202(1206) | 0 | 0 (I=0) | 0 (I=0) | 21.86(3) | LC(160gd) |
| $^{160}\mathrm{Dy}^{24+}$ | 66 | 160 | 159.925203578(751) | 0 | 0 (I=0) | 0 (I=0) | 2.329(18) | LC(160dy) |
| $^{164}\mathrm{Dy}^{24+}$ | 66 | 164 | 163.929180819(746) | 0 | 0 (I=0) | 0 (I=0) | 28.260(54) | LC(164dy) |
| $^{166}\mathrm{Er}^{26+}$ | 68 | 166 | 165.930301067(358) | 0 | 0 (I=0) | 0 (I=0) | 33.503(36) | LC(166er) |
| $^{170}\mathrm{Er}^{26+}$ | 68 | 170 | 169.935471933(1488) | 0 | 0 (I=0) | 0 (I=0) | 14.910(36) | LC(170er) |
| $^{170}\mathrm{Yb}^{28+}$ | 70 | 170 | 169.934767242(11) | 0 | 0 (I=0) | 0 (I=0) | 2.982(39) | LC(170yb) |
| $^{176}\mathrm{Yb}^{28+}$ | 70 | 176 | 175.942574706(15) | 0 | 0 (I=0) | 0 (I=0) | 12.995(83) | LC(176yb) |

## Hyperfine inputs: odd-$A$ nuclei

| Ion and isotope | $Z$ | $A$ | Neutral-atom mass (u) | $I^\pi$ ($\hbar$) | $\mu/\mu_N$ | $Q$ (b) | Natural abundance (%) / half-life | Source |
|---|---:|---:|---|---|---|---|---|---|
| $^{139}\mathrm{Ce}^{16+}$ | 58 | 139 | 138.906647029(2242) | $3/2^+$ | +1.06(4) | not evaluated in LC | no natural abundance; 137.63 d | LC(139ce) |
| $^{143}\mathrm{Nd}^{18+}$ | 60 | 143 | 142.909819815(1347) | $7/2^-$ | -1.065(5) | -0.61(2) | 12.173(26)% | LC(143nd) |
| $^{145}\mathrm{Nd}^{18+}$ | 60 | 145 | 144.912579151(1364) | $7/2^-$ | -0.656(4) | -0.314(12) | 8.293(12)% | LC(145nd) |
| $^{147}\mathrm{Sm}^{20+}$ | 62 | 147 | 146.914904401(1354) | $7/2^-$ | -0.8090(14) | -0.26(3) | 15.00(14)%; $1.073\times10^{11}$ y | LC(147sm) |
| $^{149}\mathrm{Sm}^{20+}$ | 62 | 149 | 148.917191211(1241) | $7/2^-$ | -0.6677(11) | +0.075(8) | 13.82(10)% | LC(149sm) |
| $^{155}\mathrm{Gd}^{22+}$ | 64 | 155 | 154.922629356(1055) | $3/2^-$ | -0.2591(4) | +1.27(3) | 14.80(9)% | LC(155gd) |
| $^{157}\mathrm{Gd}^{22+}$ | 64 | 157 | 156.923967424(1048) | $3/2^-$ | -0.3398(6) | +1.35(3) | 15.65(4)% | LC(157gd) |
| $^{161}\mathrm{Dy}^{24+}$ | 66 | 161 | 160.926939425(748) | $5/2^+$ | -0.479(3) | +2.51(2) | 18.889(42)% | LC(161dy) |
| $^{163}\mathrm{Dy}^{24+}$ | 66 | 163 | 162.928737221(744) | $5/2^-$ | +0.671(4) | +2.65(2) | 24.896(42)% | LC(163dy) |
| $^{167}\mathrm{Er}^{26+}$ | 68 | 167 | 166.932056192(306) | $7/2^+$ | -0.5623(4) | +3.57(3) | 22.869(9)% | LC(167er) |
| $^{171}\mathrm{Yb}^{28+}$ | 70 | 171 | 170.936331515(13) | $1/2^-$ | +0.4923(4) | 0 (I=1/2) | 14.086(140)% | LC(171yb) |
| $^{173}\mathrm{Yb}^{28+}$ | 70 | 173 | 172.938216211(12) | $5/2^-$ | -0.6780(6) | +2.80(4) | 16.103(63)% | LC(173yb) |

## Calculation-use notes and data gates

1. **Use the neutral mass only for the nuclear mass input stated here.** For a
   finite-nuclear-mass HCI calculation, obtain the ion mass consistently from
   the neutral mass by removing the appropriate number of electron rest masses
   and accounting for the total electronic binding-energy difference.  Do not
   silently insert $M_{\rm neutral}$ for an ion when the requested precision
   makes that distinction material.

2. **Separate the isotope-shift and HFS products.** The listed even-$A$
   $I=0$ pairs remove HFS at the nuclear level and are the clean baseline for
   mass/field-shift calculations.  Odd-$A$ entries are for $A$ and, where
   $Q$ is available and $I\geq1$, $B$ constants.  $^{171}$Yb supports a
   magnetic-dipole HFS test but not an electric-quadrupole $B$ benchmark.

3. **Do not plan a Ce electric-quadrupole benchmark without a new nuclear
   input decision.** The evaluated $^{139}$Ce LiveChart ground-state record
   supplies $I=3/2^+$ and $\mu$, but its $Q$ field is empty.  The older
   [NNDC/Stone moment table](https://www.nndc.bnl.gov/nndc/stone_moments/nuclear-moments.pdf)
   likewise lists $\mu$ for the ground state without an experimental $Q$.
   It can therefore test an $A$ constant if its 137.63-day source is feasible,
   but should not be used as an assumed $B$-constant target.

4. **Production feasibility is not established by natural abundance.** The
   percentages above identify naturally occurring feedstock, not enriched-
   target availability, charge-breeding efficiency, trap loading, nor nuclear
   radius data quality.  Those require a separate experimental and
   charge-radius gate before the conditional production set is frozen.
