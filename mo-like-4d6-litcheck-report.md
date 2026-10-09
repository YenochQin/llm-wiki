# Literature-landscape check — Mo-like ($4d^6$) highly charged ion dual-clock sequence

**Prepared:** 2026-09-13
**Method:** Crossref REST API, OpenAlex (title/abstract/full-text search + citation graph), Semantic Scholar API, journal-scoped OpenAlex queries (ADNDT, JQSRT, PRA), arXiv/ar5iv full text of key papers, and repeated `web_search` with varied phrasings. No paywalled full texts were read; some 2017-era data papers were assessed from title/abstract/metadata only.
**Anchor paper (verified):** C. Lyu, C. H. Keitel, Z. Harman, *Ultrastable and ultra-accurate clock transitions in open-shell highly charged ions*, **Communications Physics 8, 3 (2025)**, DOI [10.1038/s42005-024-01901-5](https://doi.org/10.1038/s42005-024-01901-5); preprint arXiv:2305.09603 (titled *Ultrastable optical, XUV and soft-x-ray clock transitions in open-shell highly charged ions*).

**Honesty statement:** every claim below is labelled **CLEAR HIT**, **AMBIGUOUS**, or **NOT FOUND**. I did not find, and did not invent, any reference that I could not open or verify through at least one bibliographic database. Where a full text was not read, that is stated.

---

## 0. Bottom line / verdict

| Proposed component | Status | Verdict |
|---|---|---|
| (a) Energies / radiative rates / lifetimes for **all 34 levels** of $4d^6$ for Ce$^{16+}$, Nd$^{18+}$, Sm$^{20+}$, Gd$^{22+}$, Dy$^{24+}$, Er$^{26+}$, Yb$^{28+}$ | **NOT FOUND (as a complete published set)** | Partial data exist for 2–3 of the 7 ions; complete $4d^6$ data exist only for *other* Z (W$^{32+}$, Sn$^{8+}$, Pd$^{4+}$) |
| (b) Isotope-shift electronic factors $K_{\rm NMS}$, $K_{\rm SMS}$, $F$ for Mo-like $4d^6$ HCIs | **NOT FOUND** | No paper found; appears genuinely open |
| (c) Hyperfine $A$ / $B$ electronic factors for Mo-like $4d^6$ HCIs | **NOT FOUND** | No paper found; appears genuinely open |
| Experimental isotope shift / HFS for any Mo-like HCI | **NOT FOUND** | Only experimental *level energies* exist (Sn$^{8+}$, Pd$^{4+}$, W$^{32+}$) |
| Dedicated experimental program on the Mo-like dual-clock ions | **NOT FOUND** (but adjacent HCI nuclear-radius programs are active) | Lyu et al. proposed it theoretically; no follow-up proposal/experiment found |

**Overall:** the *isotope-shift* and *hyperfine* parts of the proposal (b, c) look **genuinely unpublished and defensible**; the *full 34-level radiative data set for the seven named rare-earth ions* (a) also looks unpublished, **but** it is closely bordered by existing work on the same $4d^6$ isoelectronic sequence at W, Sn and Pd. Novelty will hinge on (i) doing the *whole sequence in one consistent GRASP2018 MCDHF/RCI framework*, (ii) adding IS and HFS factors that nobody has computed, and (iii) demonstrating accuracy against the existing W/Sn/Pd data.

---

## 1. Isotope-shift electronic factors ($K_{\rm NMS}$, $K_{\rm SMS}$, $F$)

**Verdict: NOT FOUND for Mo-like $4d^6$ HCIs. This is a clear gap.**

Searches performed (all returned nothing on target):
- OpenAlex `title_and_abstract.search: "isotope shift" AND "highly charged"` → 56 works, none on $4d^6$/Mo-like (the sequence is dominated by Li-like/He-like/Na-like/Xe/Ca and g-factor work).
- OpenAlex `fulltext.search: "Mo-like" AND "isotope shift"` → **3 works total**, all by Lyu/Keitel/Harman (the anchor, its arXiv version, and the 2025 PRR companion). No third-party paper.
- OpenAlex journal-scoped `fulltext.search:"Mo-like"` in **PRA → 0 works**; in **JQSRT → 0 works**.
- OpenAlex `fulltext.search:"Mo-like ions"` → **5 works total worldwide**, of which the only non-Lyu items are an unrelated NIST ionisation-potential compilation, an iodine-ion levels paper, and the 2026 Atoms Zipf-scaling paper.
- Crossref phrase searches for "Mo-like", "molybdenum-like", and per-ion notations found nothing.

The closest *analogous* published IS-factor calculations (useful as method templates and as evidence that the community considers this a publishable data product, **but they are different isoelectronic sequences**):

- **CLEAR HIT (analogue, Na-like):** S. Rathi, L. Sharma, *Extended Calculations of Atomic Structure Parameters for Na-like Ar, Kr and Xe Ions Using Relativistic MCDHF and MBPT Methods*, **Atoms 10, 131 (2022)**, DOI [10.3390/atoms10040131](https://doi.org/10.3390/atoms10040131). Abstract explicitly covers "energies, hyperfine structure constants, Landé $g_J$ factors **and isotope shifts**" for 71 states of Ar$^{7+}$, Kr$^{25+}$, Xe$^{43+}$ with GRASP2018.
- **CLEAR HIT (analogue, Ni-like/S-like):** S.-C. Yu, H. Guan, L. She, C.-B. Li, *Calculations of isotope shifts in highly charged Ni$^{12+}$ ion*, **Phys. Rev. A 113 (2026)**, DOI [10.1103/wh32-yfjk](https://doi.org/10.1103/wh32-yfjk); arXiv:2512.22850.
- **CLEAR HIT (analogue, Li-like):** D. Zhang, F. Zhang, X. Ding, C. Dong, *Isotope shift of the $2s\,^2S_{1/2}\rightarrow 2p\,^2P_{1/2,3/2}$ transitions of Li-like Ca ions*, **Chinese Physics B 30, 043102 (2020/2021)**, DOI [10.1088/1674-1056/abc7a2](https://doi.org/10.1088/1674-1056/abc7a2).
- **CLEAR HIT (analogue, Be-like, methodology):** H. Lin, S. Wu, R. Si et al., *MCDHF Calculations of Isotope Shifts for Be-like Ions Using Perturbation Theory and Finite-Field Method*, **Atoms 14, 55 (2026)**, DOI [10.3390/atoms14070055](https://doi.org/10.3390/atoms14070055).
- **CLEAR HIT (review):** B. K. Sahoo, S. A. Blundell, A. V. Oleynichenko, R. F. García Ruiz, L. V. Skripnikov, B. Ohayon, *Recent advancements in atomic many-body methods for high-precision studies of isotope shifts*, **J. Phys. B 58, 042001 (2025)**, DOI [10.1088/1361-6455/adacc1](https://doi.org/10.1088/1361-6455/adacc1). Reviews IS-factor methods in HCIs (RMBPT) and neutrals (RCC); **no Mo-like/$4d^6$ system appears** in the reviewed set I could inspect.

**Ambiguity caveat:** The OpenAlex full-text index is not complete for all publishers. It is conceivable that a recent, non-indexed paper or a conference proceedings volume contains Mo-like IS factors. I found no positive evidence of one, and the near-total absence of the phrase "Mo-like" in the ADNDT/JQSRT/PRA full-text corpora makes this unlikely.

---

## 2. Hyperfine $A$ / $B$ electronic factors for Mo-like $4d^6$ HCIs

**Verdict: NOT FOUND. Clear gap.** I checked the specific author list you gave.

- OpenAlex `title_and_abstract.search: "hyperfine" AND "highly charged"` → 191 works; the HCI hyperfine literature is dominated by **H-like, Li-like, B-like, He-like** systems (Bi$^{82+}$, Ho$^{66+}$, Pb, etc.), plus heavier many-electron cases such as I$^{7+}$. **No $4d^6$ sequence entry.**
- Searches on the named authors:
  - **Sahoo** — found only the 2025 IS review (above) and unrelated systems. **No Mo-like HFS paper.**
  - **Yu (Yan-mei Yu) & Sahoo** — the $nd^6$ clock paper (below) mentions hyperfine **only in one sentence**, as a way to reduce systematics; **no $A$/$B$ values**.
  - **Bieroń** — known for nd$^2$ HFS (e.g. Sc$^+$, Y$^+$) and the MCDHF electron–nucleus interaction machinery; **no Mo-like $4d^6$ HCI sequence paper found.**
  - **Jönsson, Ekman, Godefroid, Schiffmann** — found the modern HFS methodology paper, not $4d^6$ data: S. Schiffmann, M. Godefroid, J. Ekman, P. Jönsson, *Natural orbitals in multiconfiguration calculations of hyperfine-structure parameters*, **Phys. Rev. A 101, 062510 (2020)**, DOI [10.1103/PhysRevA.101.062510](https://doi.org/10.1103/PhysRevA.101.062510).
  - **Natarajan, Sur** — no HCI $4d^6$ HFS work surfaced.
  - **Li (Jiguang Li / Cheng-Bin Li), Chen (C. Y. Chen / Zhan-Bin Chen)** — no Mo-like HFS paper surfaced.
  - **Kimura / NIST-GRASP community** — the benchmark many-electron HCI HFS experiment is **I$^{7+}$ ($4d^9 5s$ M1)**, not $4d^6$: N. Kimura et al., *Hyperfine-structure-resolved laser spectroscopy of many-electron highly charged ions*, **Communications Physics 6, 8 (2023)**, DOI [10.1038/s42005-023-01127-x](https://doi.org/10.1038/s42005-023-01127-x).
- **Important negative:** the anchor paper itself (full text inspected) contains **no hyperfine $A$/$B$ calculations** — the word "hyperfine" appears only in introductory/general discussion. The anchor's Supplementary Information contains **only mixing coefficients** for selected $4d^4$, $4d^5$, $4d^6$ ions, not HFS or IS tables.

---

## 3. Radiative rates / lifetimes / wavelengths for the full $4d^6$ ground configuration (34 levels)

**Verdict: NOT FOUND for the seven proposed ions as a complete set. AMBIGUOUS-to-NEGATIVE on the specific "Wang et al. 2017 ADNDT on Mo-like ions" you named.**

### 3.1 The named "Wang et al. 2017 ADNDT on Mo-like ions" — I could not find it

- I enumerated **all 26 items published in ADNDT in 2017** (Crossref, ISSN 0092-640X). **None is about Mo-like ions.** The only $4d$-configuration item is Karpuškienė & Bogdanovich, *…$4p^6 4d^4$, $4p^6 4d^3 4f$ and $4p^5 4d^5$ configurations of W$^{34+}$* (that is Zr-like $4d^4$, not $4d^6$).
- OpenAlex journal-scoped **full-text** search for "Mo-like" in **all of ADNDT** returns exactly **one** paper (below, the 2023 W$^{32+}$ paper).
- Kai Wang (Beijing) is a prolific ADNDT author, but his ADNDT sequence papers are for **P-like, F-like, Cr-like, Ge-like, Si-like, As-like, Se-like, Br-like, Se XX** ions — no Mo-like/$4d^6$. Examples verified: K. Wang et al., **ADNDT 164, 101729 (2025)** (P-like Se XX), DOI [10.1016/j.adt.2025.101729](https://doi.org/10.1016/j.adt.2025.101729); Li, Guo, Wang, Si, **ADNDT 123–124, 86 (2017/2018)** (Ga-like to Br-like Gd), DOI [10.1016/j.adt.2017.11.001](https://doi.org/10.1016/j.adt.2017.11.001).
- **Likely sources of the confusion** (both real, both *not* Mo-like):
  - Z. Zhao, K. Wang, S. Li et al., *MCDHF calculations of forbidden transitions within the **$3d^k$** ground configurations of highly charged ions*, **ADNDT 119, 314 (2017/2018)**, DOI [10.1016/j.adt.2017.01.002](https://doi.org/10.1016/j.adt.2017.01.002). This is the nearest "forbidden transitions within an $nd^k$ ground configuration" ADNDT data paper — but $3d^k$, not $4d^6$.
  - Z.-B. Chen, *Ab initio calculations of atomic parameters of **Mo XVIII** of fusion interest*, **ADNDT 132, 101321 (2020)**, DOI [10.1016/j.adt.2019.101321](https://doi.org/10.1016/j.adt.2019.101321). "Mo XVIII" is the **molybdenum ion Mo$^{17+}$** (25 electrons, Mn-like), *not* the Mo-like $4d^6$ sequence — an easy citation trap.

### 3.2 What *does* exist on the $4d^6$ sequence (same configuration, other Z)

- **CLEAR HIT — complete $4d^6$ data for Mo-like W$^{32+}$:** R. Karpuškienė, R. Kisielius, *Theoretical level energies and transition data for $4p^6 4d^6$, $4p^5 4d^7$ and $4p^6 4d^5 4f$ configurations of W$^{32+}$ ion*, **ADNDT 154, 101597 (2023)**, DOI [10.1016/j.adt.2023.101597](https://doi.org/10.1016/j.adt.2023.101597). W$^{32+}$ = 42 e$^-$ = the Mo-like ion; this is the closest existing "full ground-configuration data table" for $4d^6$.
- **CLEAR HIT — W$^{29+}$–W$^{43+}$, $4p^k$/$4d^k$, M1/E2:** P. Quinet, *A theoretical survey of atomic structure and forbidden transitions in the $4p^k$ and $4d^k$ ground configurations of tungsten ions W$^{29+}$ through W$^{43+}$*, **J. Phys. B 45, 025003 (2012)**, DOI [10.1088/0953-4075/45/2/025003](https://doi.org/10.1088/0953-4075/45/2/025003). Includes $4d^6$ (W$^{32+}$).
- **CLEAR HIT (with caution) — W$^{29+}$–W$^{37+}$ $4d^N$ M1:** V. Jonauskas, G. Gaigalas, S. Kučas, **ADNDT 98, 19 (2012)**, DOI [10.1016/j.adt.2011.08.001](https://doi.org/10.1016/j.adt.2011.08.001); **Corrigendum ADNDT 119, 426 (2018)**, DOI [10.1016/j.adt.2017.08.002](https://doi.org/10.1016/j.adt.2017.08.002). Note: Quinet (2012) explicitly states his results **do not confirm** the Jonauskas ADNDT M1 values, and a corrigendum was later issued — evidence that this corner of the literature has had accuracy disputes, which is itself a novelty hook for your paper.
- **CLEAR HIT — evaluated tungsten compilation:** A. Kramida, T. Shirai, *Energy levels and spectral lines of tungsten, W III through W LXXIV*, **ADNDT 95, 1 (2009)**, DOI [10.1016/j.adt.2008.12.002](https://doi.org/10.1016/j.adt.2008.12.002) (includes Mo-like W$^{32+}$).
- **CLEAR HIT — experimental Mo-like Sn$^{8+}$ levels + CI+MBPT:** F. Torretti et al., *Optical spectroscopy of complex open-$4d$-shell ions Sn$^{7+}$–Sn$^{10+}$*, **Phys. Rev. A 95, 042503 (2017)**, DOI [10.1103/PhysRevA.95.042503](https://doi.org/10.1103/PhysRevA.95.042503). EBIT spectroscopy; **90 M1 line identifications and 79 ground-configuration energy levels** for Sn$^{7+}$–Sn$^{10+}$, i.e. including Mo-like Sn$^{8+}$ ($4d^6$); described as "the most complete data set available to date for these ground configurations".
- **CLEAR HIT — experimental Mo-like Pd$^{4+}$:** A. J. J. Raassen, Th. A. M. van Kleef, *Analysis of the fifth spectrum of palladium (Pd V)*, **Physica B+C 142, 359–374 (1986)**, DOI [10.1016/0378-4363(86)90030-6](https://doi.org/10.1016/0378-4363(86)90030-6). Pd V = Pd$^{4+}$ = 42 e$^-$ (Mo-like). Cited by Yu & Sahoo as their experimental benchmark for Mo-like $^5D_J$ splittings.

### 3.3 What exists for the *specific proposed ions*

- **CLEAR HIT (partial, competing theory paper):** Yan-mei Yu, B. K. Sahoo, *A Hunt for Highly Charged Ions as Ultra-stable Optical Clock Candidates: Art of the energy level-crossing approach*, **arXiv:2307.14543 (2023)**, [https://arxiv.org/abs/2307.14543](https://arxiv.org/abs/2307.14543). I could find **no journal version** (Crossref/OpenAlex show arXiv only). Full text inspected. It:
  - gives $^5D_J$ ($J=0$–$4$) fine-structure excitation energies for Mo-like **Sn$^{8+}$, Te$^{10+}$, Xe$^{12+}$, Ba$^{14+}$, Ce$^{16+}$, Nd$^{18+}$** (Table 2),
  - gives clock-transition $\lambda$, $\tau$, $Q$, $K_\alpha$, $\Delta R$, and reduced E2 matrix elements for Mo-like **Nd$^{18+}$ only** (Table 3),
  - uses CI+MBPT/CCSD/CISD/CISDT (AMBiT), **not** GRASP MCDHF,
  - contains **no isotope-shift factors and no hyperfine $A$/$B$**.
- **CLEAR HIT (partial, the anchor):** Lyu et al. 2025 give clock-state $\hbar\omega$ and $\tau$ for **Ce$^{16+}$ and Dy$^{24+}$** (Table 1), plus scaling figures for $^5D_{3,2,1,0}$ across Z, and state that the $nd^6$ configuration has **34 atomic states** — but publish **no complete 34-level table, no E1/M1/E2 rate table for the whole configuration, and no IS/HFS factors**. Supplementary material = mixing coefficients only.
- **NOT FOUND:** any paper giving all 34 $4d^6$ levels with radiative rates/lifetimes for Ce$^{16+}$, Nd$^{18+}$, Sm$^{20+}$, Gd$^{22+}$, Dy$^{24+}$, Er$^{26+}$, Yb$^{28+}$.

**Net for (a):** the *complete, uniform, 34-level data set for exactly these seven ions* is unpublished; but a reviewer will immediately point to W$^{32+}$ (ADNDT 2023), Quinet (2012), Jonauskas (2012/2018), Sn$^{8+}$ (Torretti 2017) and the Lyu/Yu–Sahoo clock-state values. The proposal must therefore **explicitly benchmark against those and explain what is new** (e.g. the rare-earth mid-sequence where nobody has data, plus IS/HFS).

---

## 4. Experimental isotope shift or hyperfine structure for any Mo-like HCI

**Verdict: NOT FOUND. No experimental IS or HFS measurement on a $4d^6$ Mo-like ion could be found.**

What *does* exist experimentally on Mo-like ions (levels only, no IS/HFS):

- **CLEAR HIT:** Torretti et al., **PRA 95, 042503 (2017)** — EBIT optical+EUV spectra of Sn$^{7+}$–Sn$^{10+}$ (Mo-like Sn$^{8+}$ included); levels and M1 lines only.
- **CLEAR HIT:** Raassen & van Kleef, **Physica B+C 142, 359 (1986)** — Pd V (Mo-like Pd$^{4+}$) level analysis.
- **CLEAR HIT:** Kramida & Shirai, **ADNDT 95, 1 (2009)** — evaluated W levels including Mo-like W$^{32+}$; A. N. Ryabtsev, É. Ya. Kononov, *The spectra of Cd ions with the $4d^k$ ground-state configuration: Cd IX*, **JQSRT (2026)**, DOI [10.1016/j.jqsrt.2026.110119](https://doi.org/10.1016/j.jqsrt.2026.110119) — $4d^k$-configuration spectra, but Cd IX is not $4d^6$.
- **CLEAR HIT (lanthanide HCIs, not Mo-like):** C. Suzuki et al., *Systematic Observation of EUV Spectra from Highly Charged Lanthanide Ions in the Large Helical Device*, **Atoms 6, 24 (2018)**, DOI [10.3390/atoms6020024](https://doi.org/10.3390/atoms6020024); and *Spectra of Ga-Like to Cu-Like Praseodymium and Neodymium Ions Observed in the Large Helical Device*, **Atoms 9, 46 (2021)**, DOI [10.3390/atoms9030046](https://doi.org/10.3390/atoms9030046). These cover highly charged rare-earth ions, but the published charge-state range (Ga-like to Cu-like) is far from Mo-like, and there is **no IS/HFS**.

What exists on **hyperfine-resolved HCI spectroscopy** (different configurations):

- **CLEAR HIT:** Kimura et al., **Comm. Phys. 6, 8 (2023)** — HFS-resolved laser spectroscopy of the $4d^9 5s$ M1 transition in **I$^{7+}$** (Tokyo EBIT). The only many-electron HCI HFS-resolved experiment found; **not Mo-like**.
- **CLEAR HIT:** H. Bekker et al., *Detection of the $5p$–$4f$ orbital crossing and its optical clock transition in Pr$^{9+}$*, **Nature Communications 10, 5654 (2019)**, DOI [10.1038/s41467-019-13406-9](https://doi.org/10.1038/s41467-019-13406-9) (MPIK; $4f$ open shell, not $4d^6$).
- **CLEAR HIT:** S. Chen, Z. Zhou, J. Li, T. Zhang et al., *Precision measurement of M1 optical clock transition in Ni$^{12+}$*, **Phys. Rev. Research 6, 013030 (2024)**, DOI [10.1103/PhysRevResearch.6.013030](https://doi.org/10.1103/PhysRevResearch.6.013030) (Lanzhou/IMP; S-like, not Mo-like).

**Broad experimental searches that returned nothing on target:** "isotope shift measurement Mo-like", "Mo-like hyperfine measurement", "Lanzhou EBIT Mo-like isotope shift", "Heidelberg EBIT Mo-like", "NIST EBIT Mo-like hyperfine", "Tokyo EBIT Mo-like". The Tokyo EBIT group works on Na/Mg-like Lu/Yb (below), MPIK on Ar$^{13+}$/Pr$^{9+}$/Ni$^{12+}$, Lanzhou/IMP on Ni$^{12+}$ — none on $4d^6$.

---

## 5. Active experimental program on isotope-resolved spectroscopy / nuclear-structure extraction with these ions

**Verdict: NOT FOUND for the Mo-like dual-clock ions specifically. Adjacent programs ARE active and are the correct "competitive landscape".**

- **CLEAR HIT — the closest active program (different ions):** H. Staiger, E. Takacs, S. A. Blundell, N. Kimura, H. A. Sakaue, R. F. Garcia Ruiz, W. Nazarewicz, C. Suzuki, Y. Ralchenko, I. Murakami, D. Kato, N. Nakamura et al., *Extreme Ultraviolet Spectroscopy of Highly Charged Lu and Yb Ions for Nuclear Charge Radius Determination*, **arXiv:2511.20537 (2025)**, [https://arxiv.org/abs/2511.20537](https://arxiv.org/abs/2511.20537). Tokyo EBIT + EUV spectroscopy of **Na-like and Mg-like** Lu/Yb to extract meV-level nuclear-size shifts; resolves the Lu radius anomaly. Companion: E. Takacs et al., *Puzzling Isotonic Odd-Even Staggering of Charge Radii in Deformed Rare Earth Nuclei*, **arXiv:2511.19395 (2025)**, [https://arxiv.org/abs/2511.19395](https://arxiv.org/abs/2511.19395). This group is explicitly doing "isotope/element-resolved HCI spectroscopy → nuclear charge radii" on rare earths — but with Na/Mg-like ions, **not** Mo-like $4d^6$.
- **CLEAR HIT — Ca-like coronal-line IS proposal (MPIK):** N.-H. Rehbehn, M. K. Rosner, H. Bekker, J. C. Berengut, P. O. Schmidt, S. A. King, P. Micke, M. F. Gu, R. Müller, A. Surzhykov, J. R. Crespo López-Urrutia, *Sensitivity to new physics of isotope-shift studies using the coronal lines of highly charged calcium ions*, **Phys. Rev. A 103, L040801 (2021)**, DOI [10.1103/PhysRevA.103.L040801](https://doi.org/10.1103/PhysRevA.103.L040801). And N.-H. Rehbehn et al., *Narrow and Ultranarrow Transitions in Highly Charged Xe Ions as Probes of Fifth Forces*, **PRL 131, 161803 (2023)**, DOI [10.1103/PhysRevLett.131.161803](https://doi.org/10.1103/PhysRevLett.131.161803).
- **CLEAR HIT — MPIK/PTB HCI optical-clock infrastructure (methods, no Mo-like proposal):** S. Chen, L. J. Spieß, A. Wilzewski, M. Wehrheim, K. Dietze, I. Vybornyi, K. Hammerer, J. R. Crespo López-Urrutia, *Identification of highly forbidden optical transitions in highly charged ions*, **Phys. Rev. Applied 22, 054059 (2024)**, DOI [10.1103/PhysRevApplied.22.054059](https://doi.org/10.1103/PhysRevApplied.22.054059); S. A. King et al., *An optical atomic clock based on a highly charged ion*, **Nature 611, 43 (2022)**, DOI [10.1038/s41586-022-05245-4](https://doi.org/10.1038/s41586-022-05245-4).
- **CLEAR HIT — the anchor's own forward-looking statement (motivation, not a program):** Lyu et al. 2025 conclude that "high-precision spectroscopy of these transitions would enable an accurate determination of nuclear parameters for more than 70 elements and their isotopes", and cite the nuclear-radius literature. That is a *motivation*, not an experimental proposal.
- **CLEAR HIT — a 2026 statistical/crank-adjacent follow-up that exploits the $nd^6$ data:** A. F. Fuck da Silva, S. da Silva, R. Matsushita, G. F. Caramori, *Thresholded Zipf Scaling Across 14 Highly-Charged-Ion Isoelectric Sequences: Identification of an $nd^6\,{}^5D_0$ $jj$-Coupling Pair*, **Atoms 14, 60 (2026)**, DOI [10.3390/atoms14070060](https://doi.org/10.3390/atoms14070060). Cites Lyu et al.; explicitly says it uses "**digitization of GRASP MCDHF Mo-like results**" (i.e. re-uses the anchor's numbers, publishes no new atomic data). Relevant only as evidence that the $nd^6$ sequence is attracting attention and that **quantitative GRASP tables are in demand**.
- **CLEAR HIT — companion theory paper by the anchor authors:** C. Lyu, C. H. Keitel, Z. Harman, *Periodic table for highly charged ions*, **Phys. Rev. Research (2025)**, DOI [10.1103/bppp-53g1](https://doi.org/10.1103/bppp-53g1); arXiv:2504.11237. Framing/scaling paper, no IS/HFS factors.

**Net for (5):** Nobody has (yet) published a dedicated proposal or experiment for isotope-resolved spectroscopy of the Mo-like $4d^6$ dual-clock ions, and the anchor paper does not cite one. This is an open flank — but note the Tokyo/RIKEN EUV program is already doing the *nuclear-radius* science on Na/Mg-like rare earths, so the "selling point" of the Mo-like system must be argued (e.g. optical-clock-grade systematic control, dual-clock $\alpha$-sensitivity cancellation, $Q\sim10^{17}$–$10^{18}$).

---

## 6. Venues and the expected novelty bar for "new atomic data for HCIs"

### Typical venues (all verified with recent examples)

| Venue | What it accepts | Recent concrete example |
|---|---|---|
| **Atomic Data and Nuclear Data Tables (ADNDT)** | Comprehensive, tabulated, *critically evaluated* data for a full configuration/sequence; strong emphasis on accuracy assessment, convergence, and comparison with prior work. Highest bar for completeness. | Karpuškienė & Kisielius, **ADNDT 154, 101597 (2023)** [10.1016/j.adt.2023.101597](https://doi.org/10.1016/j.adt.2023.101597); Wang et al., **ADNDT 164, 101729 (2025)** [10.1016/j.adt.2025.101729](https://doi.org/10.1016/j.adt.2025.101729); Gaigalas, Rynkun, Radžiūtė, Jönsson, **ADNDT 141, 101428 (2021)** [10.1016/j.adt.2021.101428](https://doi.org/10.1016/j.adt.2021.101428) |
| **Physical Review A** | Data sets *plus* a physics result, benchmark accuracy, or direct theory–experiment confrontation. | Yu et al., **PRA 113 (2026)** (Ni$^{12+}$ IS, tied to the Lanzhou measurement) [10.1103/wh32-yfjk](https://doi.org/10.1103/wh32-yfjk) |
| **Journal of Physics B (J. Phys. B)** | Methodologically framed structure/transition calculations, benchmark comparisons, atomic-data surveys. | Quinet, **J. Phys. B 45, 025003 (2012)** [10.1088/0953-4075/45/2/025003](https://doi.org/10.1088/0953-4075/45/2/025003); Sahoo et al., **J. Phys. B 58, 042001 (2025)** [10.1088/1361-6455/adacc1](https://doi.org/10.1088/1361-6455/adacc1) |
| **Atoms (MDPI, open access)** | "Extended calculations of atomic structure parameters" including hyperfine and isotope-shift factors; the most common home for GRASP2018 data papers of the type proposed. Fast, lower bar, but still reviewed. | Rathi & Sharma, **Atoms 10, 131 (2022)** [10.3390/atoms10040131](https://doi.org/10.3390/atoms10040131); Zhang, Wu, Dong, Ding, **Atoms 13, 54 (2025)** [10.3390/atoms13060054](https://doi.org/10.3390/atoms13060054); Lin, Wu, Si et al., **Atoms 14, 55 (2026)** [10.3390/atoms14070055](https://doi.org/10.3390/atoms14070055) |
| **JQSRT** | Spectra, wavelengths, transition probabilities with plasma/astrophysical or metrology application. | Ryabtsev & Kononov, **JQSRT (2026)** (Cd IX $4d^k$) [10.1016/j.jqsrt.2026.110119](https://doi.org/10.1016/j.jqsrt.2026.110119) |
| **Phys. Rev. Research / Communications Physics** | Higher-profile, requires a strong physics narrative beyond the data tables. | Lyu, Keitel, Harman, **Comm. Phys. 8, 3 (2025)**; **PRR (2025)** [10.1103/bppp-53g1](https://doi.org/10.1103/bppp-53g1) |

### How recent similar papers justified novelty (verified from abstracts/text)

1. **Rathi & Sharma (Atoms 2022)** — novelty = *scope/coverage*: "comprehensive calculations of energies, hyperfine structure constants, Landé $g_J$ factors and isotope shifts … for the lowest **71 states**", plus a systematic analysis of Breit/QED effects. This is the single closest template for your proposal: same code (GRASP2018 MCDHF/RCI), same combination of energies + $A/B$ + IS + rates, different isoelectronic sequence.
2. **Karpuškienė & Kisielius (ADNDT 2023)** — novelty = *first complete transition data for three interacting configurations of an ion* (W$^{32+}$: $4p^6 4d^6$, $4p^5 4d^7$, $4p^6 4d^5 4f$), extending their prior W$^{34+}$ work, with explicit comparison to earlier compilations and CI-effect analysis.
3. **Torretti et al. (PRA 2017)** — novelty = *experiment/theory confrontation*: "the most complete data set available to date for these ground configurations", **90 line identifications and 79 levels**, and it "question[s] some earlier EUV-line assignments". Beware: an analogous claim in your paper would collide with theirs if you go below Z≈50.
4. **Quinet (J. Phys. B 2012)** — novelty = *resolving a discrepancy*: explicitly argues that a prior ADNDT work (Jonauskas et al. 2012) is wrong for many M1 lines. Later a corrigendum confirmed the problem. **A paper that adjudicates accuracy for the $4d^6$ sequence is demonstrably publishable.**
5. **Yu & Sahoo (arXiv 2023)** — novelty = *identifying new clock candidates via energy-level crossing* and quantifying $Q$, $\alpha$-sensitivity and systematics. Your proposal competes directly with this for Ce$^{16+}$/Nd$^{18+}$ energies/rates; differentiate by the full 34-level set + IS/HFS and by the consistent GRASP2018 MCDHF/RCI framework (they used CI+MBPT/CCSD/CISDT).
6. **Zhang et al. (Atoms 2025)** — novelty = *configuration resolution* + probing $\alpha$ variation for Pr$^{9+}$/Nd$^{10+}$; a template for "MCDHF data + a fundamental-physics hook" in Atoms.

### What the bar implies for this proposal

- **ADNDT** would require: all 34 levels for **all seven ions** (or a stated, justified subset), energies *and* wavelengths *and* E1/M1/E2 rates *and* lifetimes, convergence/uncertainty estimates, and explicit numerical comparison with Karpuškienė (2023), Quinet (2012), Jonauskas (2012/2018), Kramida & Shirai (2009), Torretti (2017), and Lyu (2025)/Yu–Sahoo (2023). IS and HFS factors would be a genuine bonus.
- **PRA / J. Phys. B / Atoms** would accept a narrower paper, but need a clear "why now / what is new" statement. The strongest defensible novelty claims are: (i) **first IS factors ($K_{\rm NMS}, K_{\rm SMS}, F$) for the Mo-like clock sequence**; (ii) **first hyperfine $A/B$ for the same**; (iii) **first uniform 34-level GRASP2018 data set across Ce→Yb**, filling the mid-sequence gap left by W$^{32+}$ and Sn$^{8+}$; (iv) adjudicating the $4d^6$ rate discrepancies flagged by Quinet (2012).

---

## 7. Confidence and residual uncertainty

- **High confidence:** the anchor paper contains no IS/HFS factors and no full 34-level table (full text and supplementary inspected). ADNDT has exactly one $4d^6$-sequence data paper (W$^{32+}$, 2023) and **no 2017 Mo-like paper**. The named authors (Sahoo, Yu, Bieroń, Jönsson, Ekman, Schiffmann, Godefroid, Natarajan, Sur, Li, Chen) have no $4d^6$ Mo-like HFS paper that I could find.
- **Medium confidence:** that *no one anywhere* has computed IS factors for these ions. The phrase "Mo-like" is nearly absent from the indexed full-text corpora (5 works total), which is consistent with a gap but also means a paper that never uses the term would be missed by full-text search. I mitigated this by searching IS+HCI broadly (56 works) and by author.
- **Low confidence / unverified:** I could not read paywalled full texts of Karpuškienė & Kisielius (2023), Quinet (2012), Jonauskas (2012), Torretti (2017), or Kramida & Shirai (2009); their scope is inferred from titles/abstracts/secondary descriptions. If any of these turns out to contain IS or HFS factors, that would change the verdict — but none of the titles/abstracts suggest it.
- **Not searched:** Google Scholar (paywall/robots), Web of Science/Scopus (key-gated), INSPIRE, and non-English (Chinese/Japanese) journal literature beyond what surfaced incidentally. A Chinese-language paper on $4d^6$ HCI data could exist (e.g. in *Acta Physica Sinica*), though the group publishing there (Wang Jia, Yan, Acta Phys. Sin. 2023 on Al-like HCI hyperfine) works other sequences.
- **arXiv API was rate-limited (HTTP 429)** during this check, so the most recent (last few weeks) arXiv postings may not be fully covered. OpenAlex/Crossref (which index arXiv) showed nothing relevant, but a *very* recent preprint could have been missed.

---

## 8. Full reference list (all verified)

1. C. Lyu, C. H. Keitel, Z. Harman, *Ultrastable and ultra-accurate clock transitions in open-shell highly charged ions*, Communications Physics **8**, 3 (2025). DOI [10.1038/s42005-024-01901-5](https://doi.org/10.1038/s42005-024-01901-5). Preprint: arXiv:2305.09603, [https://arxiv.org/abs/2305.09603](https://arxiv.org/abs/2305.09603).
2. C. Lyu, C. H. Keitel, Z. Harman, *Periodic table for highly charged ions*, Phys. Rev. Research (2025). DOI [10.1103/bppp-53g1](https://doi.org/10.1103/bppp-53g1). arXiv:2504.11237.
3. Yan-mei Yu, B. K. Sahoo, *A Hunt for Highly Charged Ions as Ultra-stable Optical Clock Candidates: Art of the energy level-crossing approach*, arXiv:2307.14543 (2023). [https://arxiv.org/abs/2307.14543](https://arxiv.org/abs/2307.14543).
4. R. Karpuškienė, R. Kisielius, *Theoretical level energies and transition data for $4p^6 4d^6$, $4p^5 4d^7$ and $4p^6 4d^5 4f$ configurations of W$^{32+}$ ion*, Atomic Data and Nuclear Data Tables **154**, 101597 (2023). DOI [10.1016/j.adt.2023.101597](https://doi.org/10.1016/j.adt.2023.101597).
5. P. Quinet, *A theoretical survey of atomic structure and forbidden transitions in the $4p^k$ and $4d^k$ ground configurations of tungsten ions W$^{29+}$ through W$^{43+}$*, J. Phys. B **45**, 025003 (2012). DOI [10.1088/0953-4075/45/2/025003](https://doi.org/10.1088/0953-4075/45/2/025003).
6. V. Jonauskas, G. Gaigalas, S. Kučas, *Relativistic calculations for M1-type transitions in $4d^N$ configurations of W$^{29+}$–W$^{37+}$ ions*, Atomic Data and Nuclear Data Tables **98**, 19 (2012). DOI [10.1016/j.adt.2011.08.001](https://doi.org/10.1016/j.adt.2011.08.001). Corrigendum: ADNDT **119**, 426 (2018), DOI [10.1016/j.adt.2017.08.002](https://doi.org/10.1016/j.adt.2017.08.002).
7. F. Torretti, A. Windberger, A. Ryabtsev, S. Dobrodey, H. Bekker, W. Ubachs, R. Hoekstra, E. V. Kahl, J. C. Berengut, J. R. Crespo López-Urrutia, *Optical spectroscopy of complex open-$4d$-shell ions Sn$^{7+}$–Sn$^{10+}$*, Phys. Rev. A **95**, 042503 (2017). DOI [10.1103/PhysRevA.95.042503](https://doi.org/10.1103/PhysRevA.95.042503).
8. A. J. J. Raassen, Th. A. M. van Kleef, *Analysis of the fifth spectrum of palladium (Pd V)*, Physica B+C **142**, 359–374 (1986). DOI [10.1016/0378-4363(86)90030-6](https://doi.org/10.1016/0378-4363(86)90030-6).
9. A. Kramida, T. Shirai, *Energy levels and spectral lines of tungsten, W III through W LXXIV*, Atomic Data and Nuclear Data Tables **95**, 1 (2009). DOI [10.1016/j.adt.2008.12.002](https://doi.org/10.1016/j.adt.2008.12.002).
10. J. Sugar, A. Musgrove, *Energy Levels of Molybdenum, Mo I through Mo XLII*, J. Phys. Chem. Ref. Data **17**, 155 (1988). DOI [10.1063/1.555818](https://doi.org/10.1063/1.555818).
11. Z. Zhao, K. Wang, S. Li et al., *Multi-configuration Dirac–Hartree–Fock calculations of forbidden transitions within the $3d^k$ ground configurations of highly charged ions*, Atomic Data and Nuclear Data Tables **119**, 314 (2017/2018). DOI [10.1016/j.adt.2017.01.002](https://doi.org/10.1016/j.adt.2017.01.002).
12. Z.-B. Chen, *Ab initio calculations of atomic parameters of Mo XVIII of fusion interest*, Atomic Data and Nuclear Data Tables **132**, 101321 (2020). DOI [10.1016/j.adt.2019.101321](https://doi.org/10.1016/j.adt.2019.101321).
13. S. Rathi, L. Sharma, *Extended Calculations of Atomic Structure Parameters for Na-like Ar, Kr and Xe Ions Using Relativistic MCDHF and MBPT Methods*, Atoms **10**, 131 (2022). DOI [10.3390/atoms10040131](https://doi.org/10.3390/atoms10040131).
14. B. K. Sahoo, S. A. Blundell, A. V. Oleynichenko, R. F. García Ruiz, L. V. Skripnikov, B. Ohayon, *Recent advancements in atomic many-body methods for high-precision studies of isotope shifts*, J. Phys. B **58**, 042001 (2025). DOI [10.1088/1361-6455/adacc1](https://doi.org/10.1088/1361-6455/adacc1).
15. S.-C. Yu, H. Guan, L. She, C.-B. Li, *Calculations of isotope shifts in highly charged Ni$^{12+}$ ion*, Phys. Rev. A **113** (2026). DOI [10.1103/wh32-yfjk](https://doi.org/10.1103/wh32-yfjk). arXiv:2512.22850.
16. D. Zhang, F. Zhang, X. Ding, C. Dong, *Isotope shift of the $2s\,^2S_{1/2}\rightarrow 2p\,^2P_{1/2,3/2}$ transitions of Li-like Ca ions*, Chinese Physics B **30**, 043102 (2020/2021). DOI [10.1088/1674-1056/abc7a2](https://doi.org/10.1088/1674-1056/abc7a2).
17. H. Lin, S. Wu, R. Si et al., *MCDHF Calculations of Isotope Shifts for Be-like Ions Using Perturbation Theory and Finite-Field Method*, Atoms **14**, 55 (2026). DOI [10.3390/atoms14070055](https://doi.org/10.3390/atoms14070055).
18. S. Schiffmann, M. Godefroid, J. Ekman, P. Jönsson, *Natural orbitals in multiconfiguration calculations of hyperfine-structure parameters*, Phys. Rev. A **101**, 062510 (2020). DOI [10.1103/PhysRevA.101.062510](https://doi.org/10.1103/PhysRevA.101.062510).
19. N. Kimura, Priti, Y. Kono, P. Pipatpakorn et al., *Hyperfine-structure-resolved laser spectroscopy of many-electron highly charged ions*, Communications Physics **6**, 8 (2023). DOI [10.1038/s42005-023-01127-x](https://doi.org/10.1038/s42005-023-01127-x).
20. S. Chen, L. J. Spieß, A. Wilzewski, M. Wehrheim, K. Dietze, I. Vybornyi, K. Hammerer, J. R. Crespo López-Urrutia, *Identification of highly forbidden optical transitions in highly charged ions*, Phys. Rev. Applied **22**, 054059 (2024). DOI [10.1103/PhysRevApplied.22.054059](https://doi.org/10.1103/PhysRevApplied.22.054059).
21. S. Chen, Z. Zhou, J. Li, T. Zhang et al., *Precision measurement of M1 optical clock transition in Ni$^{12+}$*, Phys. Rev. Research **6**, 013030 (2024). DOI [10.1103/PhysRevResearch.6.013030](https://doi.org/10.1103/PhysRevResearch.6.013030).
22. H. Bekker, A. Borschevsky, Z. Harman, C. H. Keitel et al., *Detection of the $5p$–$4f$ orbital crossing and its optical clock transition in Pr$^{9+}$*, Nature Communications **10**, 5651 (2019). DOI [10.1038/s41467-019-13406-9](https://doi.org/10.1038/s41467-019-13406-9).
23. S. A. King, L. J. Spieß, P. Micke, A. Wilzewski et al., *An optical atomic clock based on a highly charged ion*, Nature **611**, 43 (2022). DOI [10.1038/s41586-022-05245-4](https://doi.org/10.1038/s41586-022-05245-4).
24. N.-H. Rehbehn, M. K. Rosner, H. Bekker, J. C. Berengut et al., *Sensitivity to new physics of isotope-shift studies using the coronal lines of highly charged calcium ions*, Phys. Rev. A **103**, L040801 (2021). DOI [10.1103/PhysRevA.103.L040801](https://doi.org/10.1103/PhysRevA.103.L040801).
25. H. Staiger, E. Takacs, S. A. Blundell, N. Kimura, H. A. Sakaue, R. F. Garcia Ruiz, W. Nazarewicz, C. Suzuki, Y. Ralchenko, I. Murakami, D. Kato, N. Nakamura et al., *Extreme Ultraviolet Spectroscopy of Highly Charged Lu and Yb Ions for Nuclear Charge Radius Determination*, arXiv:2511.20537 (2025). [https://arxiv.org/abs/2511.20537](https://arxiv.org/abs/2511.20537).
26. E. Takacs, H. Staiger, S. A. Blundell, N. Kimura et al., *Puzzling Isotonic Odd-Even Staggering of Charge Radii in Deformed Rare Earth Nuclei*, arXiv:2511.19395 (2025). [https://arxiv.org/abs/2511.19395](https://arxiv.org/abs/2511.19395).
27. C. Suzuki, F. Koike, I. Murakami, N. Tamura et al., *Systematic Observation of EUV Spectra from Highly Charged Lanthanide Ions in the Large Helical Device*, Atoms **6**, 24 (2018). DOI [10.3390/atoms6020024](https://doi.org/10.3390/atoms6020024).
28. C. Suzuki, F. Koike, I. Murakami, T. Oishi et al., *Spectra of Ga-Like to Cu-Like Praseodymium and Neodymium Ions Observed in the Large Helical Device*, Atoms **9**, 46 (2021). DOI [10.3390/atoms9030046](https://doi.org/10.3390/atoms9030046).
29. A. N. Ryabtsev, É. Ya. Kononov, *The spectra of Cd ions with the $4d^k$ ground-state configuration: Cd IX*, JQSRT (2026). DOI [10.1016/j.jqsrt.2026.110119](https://doi.org/10.1016/j.jqsrt.2026.110119).
30. A. F. Fuck da Silva, S. da Silva, R. Matsushita, G. F. Caramori, *Thresholded Zipf Scaling Across 14 Highly-Charged-Ion Isoelectronic Sequences: Identification of an $nd^6\,{}^5D_0$ $jj$-Coupling Pair*, Atoms **14**, 60 (2026). DOI [10.3390/atoms14070060](https://doi.org/10.3390/atoms14070060).
31. S. Zhang, C. Wu, C. Dong, X. Ding, *Multi-Configuration Dirac–Hartree–Fock Calculations of Pr$^{9+}$ and Nd$^{10+}$: Configuration Resolution and Probing Fine-Structure Constant Variation*, Atoms **13**, 54 (2025). DOI [10.3390/atoms13060054](https://doi.org/10.3390/atoms13060054).
32. K. Wang, X. Bai, C. Y. Chen, J. Yan, *Extended calculations of energy levels, radiative properties, and lifetimes for phosphorus-like Se XX*, Atomic Data and Nuclear Data Tables **164**, 101729 (2025). DOI [10.1016/j.adt.2025.101729](https://doi.org/10.1016/j.adt.2025.101729).
33. M. C. Li, X. L. Guo, K. Wang, R. Si et al., *High-accuracy MCDHF calculations of the energy levels and transition properties of Ga-like to Br-like gadolinium ions*, Atomic Data and Nuclear Data Tables **123–124**, 86 (2017/2018). DOI [10.1016/j.adt.2017.11.001](https://doi.org/10.1016/j.adt.2017.11.001).
34. G. Gaigalas, P. Rynkun, L. Radžiūtė, P. Jönsson, *Energy and transition data computations for P-like ions: As, Kr, Sr, Zr, Mo, and W*, Atomic Data and Nuclear Data Tables **141**, 101428 (2021). DOI [10.1016/j.adt.2021.101428](https://doi.org/10.1016/j.adt.2021.101428).
35. C. Froese Fischer, G. Gaigalas, P. Jönsson, J. Bieroń, *GRASP2018 — a Fortran 95 version of the General Relativistic Atomic Structure Package*, Comput. Phys. Commun. **237**, 184 (2019). DOI [10.1016/j.cpc.2018.10.032](https://doi.org/10.1016/j.cpc.2018.10.032).
