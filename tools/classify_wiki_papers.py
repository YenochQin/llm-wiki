#!/usr/bin/env python3
"""Match wiki paper pages to Zotero items and propose additive collections.

This tool is intentionally a report/assignment generator. It never writes
Zotero data; ``tools/zotero_client.py assign`` performs the explicit additive
write through the installed Zotero plugin.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests
import yaml

DEFAULT_WIKI = Path("/home/yenoch/Projects/ObsidianFiles/ObsidianVaults/YenochWiki/wiki")
DEFAULT_API = "http://127.0.0.1:23119"
HEADERS = {"Zotero-Allowed-Request": "1", "User-Agent": "llm-wiki-zotero-read/0.1"}

# Leaf display names. The key is resolved against the live collection listing,
# so no stale Zotero collection key is embedded in this report generator.
CATEGORIES = [
    "MCDHF and RCI", "GRASP and Atomic-Structure Software", "CI-MBPT and CI-All-Order",
    "Electron Correlation and CSF Selection", "Relativistic, Breit, and QED Effects",
    "Open d-Shell Atoms", "Open f-Shell Atoms", "Energy Levels and Term Identification",
    "Transition Data and Lifetimes", "Hyperfine Constants", "Nuclear Moments",
    "Nuclear Size and Shape", "Isotope-Shift Theory and Calculations", "Nuclear Charge Radii",
    "King Plots and New Physics", "Stellar Atmospheres and Abundances", "Plasma Diagnostics",
    "Kilonova Opacity", "Atomic Databases",
]

# We score normalized YAML metadata and the paper title/body. Rules are kept
# explicit and conservative so the report is auditable and reproducible.
RULES: dict[str, list[tuple[str, int]]] = {
    "MCDHF and RCI": [(r"\bmcdhf\b|mcdf|rci|dirac.?hartree.?fock", 5)],
    "GRASP and Atomic-Structure Software": [(r"grasp|hullac|fac\b|autostructure|cowan|atsp|ambit|atomic code|software package", 5)],
    "CI-MBPT and CI-All-Order": [(r"ci\+?mbpt|many.?body perturbation|mbpt|coupled.?cluster|all.?order|fscc|ccsd", 5)],
    "Electron Correlation and CSF Selection": [(r"electron correlation|configuration interaction|configuration state function|\bcsf\b|active.?space|selected.?ci|configuration mixing", 4)],
    "Relativistic, Breit, and QED Effects": [(r"relativistic|breit|qed|dirac.?coulomb|vacuum polarization|self.?energy|finite nuclear size", 4)],
    # Avoid one-letter element symbols (V/U) and optional empty ionization
    # suffixes: those patterns otherwise match ordinary words in prose.
    "Open d-Shell Atoms": [(r"open.?d.?shell|d.?shell|transition.?metal|\b(?:fe|ni|co|cr|mn|ti|sc|zn|cu)\s+(?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\b|iron|nickel|cobalt|chromium|manganese|titanium|scandium|zinc|copper", 5)],
    "Open f-Shell Atoms": [(r"open.?f.?shell|f.?shell|lanthanide|actinide|rare.?earth|\b(?:ce|pr|nd|sm|eu|gd|tb|dy|ho|er|tm|yb|lu|th|pu)\s+(?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\b|cerium|praseodymium|neodymium|samarium|europium|gadolinium|terbium|dysprosium|holmium|erbium|thulium|ytterbium|lutetium|thorium|plutonium", 5)],
    "Energy Levels and Term Identification": [(r"energy levels?|term identification|level classification|line identification|spectral classification|fine.?structure levels", 4)],
    "Transition Data and Lifetimes": [(r"transition (probabilit|rat|data)|oscillator strength|radiative lifetime|lifetimes?|branching fraction|einstein [ab] coefficient", 4)],
    "Hyperfine Constants": [(r"hyperfine (structure )?constant|hyperfine constants|a.? and b.? constants|magnetic dipole hyperfine|electric quadrupole hyperfine", 5)],
    "Nuclear Moments": [(r"nuclear moments?|magnetic dipole moment|electric quadrupole moment|nuclear g.?factor|bohr.?weisskopf", 5)],
    "Nuclear Size and Shape": [(r"nuclear (size|shape|deformation|radius|radii)|charge distribution|finite.?size effect", 4)],
    "Isotope-Shift Theory and Calculations": [(r"isotope shift|isotopic shift|mass shift|field shift|specific mass shift", 5)],
    "Nuclear Charge Radii": [(r"nuclear charge radii?|charge radius|charge radii|isotope radii", 5)],
    "King Plots and New Physics": [(r"king.?plot|new physics|beyond the standard model|fundamental constant variation|nonlinearity", 6)],
    "Stellar Atmospheres and Abundances": [(r"stellar atmospheres?|stellar abundance|chemical abundances?|photosphere|spectral synthesis|stellar spectroscopy", 6)],
    "Plasma Diagnostics": [(r"plasma diagnostic|collisional.?radiative|ebit|electron beam ion trap|fusion plasma|tokamak|plasma spectroscopy", 6)],
    "Kilonova Opacity": [(r"kilonova|expansion opacity|neutron star merger|r.?process ejecta|lanthanide opacity", 7)],
    "Atomic Databases": [(r"atomic database|atomic data (?:for|and)|nist database|chianti|vald|spectroscopic database|line list|data compilation", 4)],
}


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def doi_norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", text)
    return text.rstrip(" .;)")


def parse_pages(root: Path) -> list[dict[str, Any]]:
    pages = []
    for path in sorted((root / "papers").glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        front: dict[str, Any] = {}
        if text.startswith("---"):
            try:
                front = yaml.safe_load(text.split("---", 2)[1]) or {}
            except yaml.YAMLError:
                front = {}
        metadata = " ".join(
            [str(front.get(k, "")) for k in
             ("title", "tags", "research_modes", "theory_tags", "computation_tags",
              "experiment_tags", "research_object_tags", "domain", "venue")]
        )
        # Interpretive sections are curated by the wiki pipeline. Exclude the
        # Evidence Pack and bibliography, whose quoted citations otherwise
        # create false method/application hits (e.g. a stellar-abundance
        # review mentioning MCDHF only in its references).
        body_parts = []
        for heading in ("## Problem", "## Key idea", "## Research classification"):
            if heading in text:
                part = text.split(heading, 1)[1]
                part = re.split(r"\n## ", part, maxsplit=1)[0]
                body_parts.append(part[:3500])
        body = " ".join(body_parts)
        external_ids = front.get("external_ids") or {}
        doi_value = next((v for k, v in external_ids.items() if str(k).lower() == "doi"), "")
        pages.append({
            "slug": path.stem,
            "path": str(path),
            "title": str(front.get("title") or ""),
            "doi": doi_norm(doi_value),
            "citationKey": str(front.get("citationKey") or "").strip(),
            "year": str(front.get("year") or ""),
            "text": (metadata + " " + body),
        })
    return pages


def fetch_items(api: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    start = 0
    while True:
        response = requests.get(
            f"{api}/api/users/0/items/top", params={"limit": 100, "start": start, "include": "data"},
            headers=HEADERS, timeout=(5, 60),
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        result.extend(batch)
        if len(batch) < 100:
            break
        start += len(batch)
    return result


def item_record(item: dict[str, Any]) -> dict[str, Any]:
    data = item.get("data") or {}
    creators = " ".join(
        f"{c.get('lastName', '')} {c.get('firstName', '')}" for c in data.get("creators", [])
    )
    return {
        "key": item.get("key"), "title": str(data.get("title") or ""),
        "doi": doi_norm(data.get("DOI")), "citationKey": str(data.get("citationKey") or ""),
        "year": str(data.get("date") or "")[:4], "creators": creators,
        "collections": list(data.get("collections") or []),
    }


def match_page(page: dict[str, Any], items: list[dict[str, Any]], by_doi: dict[str, list[dict[str, Any]]], by_ck: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any] | None, str, float]:
    if page["doi"] and page["doi"] in by_doi:
        candidates = by_doi[page["doi"]]
        if len(candidates) == 1:
            return candidates[0], "doi", 1.0
        return None, "ambiguous-doi", 0.0
    if page["citationKey"] and page["citationKey"].lower() in by_ck:
        candidates = by_ck[page["citationKey"].lower()]
        if len(candidates) == 1:
            return candidates[0], "citationKey", 0.98
    title = norm(page["title"])
    if not title:
        return None, "no-identifier", 0.0
    best: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        ititle = norm(item["title"])
        if not ititle:
            continue
        score = 0.0
        if title == ititle:
            score = 0.92
        elif title in ititle or ititle in title:
            score = 0.78
        else:
            a = set(title.split()); b = set(ititle.split())
            overlap = len(a & b) / max(1, len(a | b))
            if overlap >= 0.82:
                score = 0.72
        if score:
            if page["year"] and item["year"] and page["year"] == item["year"]:
                score += 0.04
            best.append((score, item))
    best.sort(key=lambda x: x[0], reverse=True)
    if best and (len(best) == 1 or best[0][0] - best[1][0] >= 0.08) and best[0][0] >= 0.82:
        return best[0][1], "title", best[0][0]
    return None, "unresolved", best[0][0] if best else 0.0


def classify(text: str) -> list[tuple[str, int]]:
    text = norm(text)
    scored = []
    for category, rules in RULES.items():
        score = sum(weight for pattern, weight in rules if re.search(pattern, text, re.I))
        if score:
            scored.append((category, score))
    scored.sort(key=lambda x: (-x[1], CATEGORIES.index(x[0])))
    if not scored:
        return []
    # Keep all strong independent signals, but avoid dumping broad papers into
    # every method bucket. At least one category is always returned.
    top = scored[0][1]
    return [(cat, score) for cat, score in scored if score >= max(4, top - 3)][:5]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pages = parse_pages(args.wiki_root)
    items = [item_record(item) for item in fetch_items(args.api)]
    by_doi: dict[str, list[dict[str, Any]]] = {}
    by_ck: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if item["doi"]: by_doi.setdefault(item["doi"], []).append(item)
        if item["citationKey"]: by_ck.setdefault(item["citationKey"].lower(), []).append(item)
    matches = []
    unresolved = []
    for page in pages:
        item, method, confidence = match_page(page, items, by_doi, by_ck)
        categories = classify(page["text"])
        record = {"slug": page["slug"], "title": page["title"], "doi": page["doi"],
                  "matchMethod": method, "matchConfidence": confidence,
                  "item": item, "categories": [{"name": c, "score": s} for c, s in categories]}
        if item and categories:
            matches.append(record)
        else:
            unresolved.append(record)
    assignments = []
    for record in matches:
        assignments.append({"slug": record["slug"], "itemKey": record["item"]["key"],
                            "categories": [c["name"] for c in record["categories"]]})
    output = {"wikiPaperCount": len(pages), "zoteroTopLevelItemCount": len(items),
              "matchedAndClassified": len(matches), "unresolvedOrUnclassified": len(unresolved),
              "matches": matches, "unresolved": unresolved, "assignments": assignments}
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("wikiPaperCount", "zoteroTopLevelItemCount", "matchedAndClassified", "unresolvedOrUnclassified")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
