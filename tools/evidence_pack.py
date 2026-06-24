#!/usr/bin/env python3
"""Render canonical Evidence Pack markdown from structured card parameters."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EVIDENCE_ID_RE = re.compile(r"^E[1-9][0-9]*$")
SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


@dataclass(frozen=True)
class EvidenceCard:
    evidence_id: str
    use_label: str
    short_label: str
    source_slug: str
    source_section: str
    excerpt: str

    def __post_init__(self) -> None:
        if not EVIDENCE_ID_RE.match(self.evidence_id):
            raise ValueError(f"evidence_id must look like E1, got {self.evidence_id!r}")
        if not self.use_label.strip():
            raise ValueError("use_label must not be empty")
        if not self.short_label.strip():
            raise ValueError("short_label must not be empty")
        if not SLUG_RE.match(self.source_slug):
            raise ValueError(f"source_slug must be a slug, got {self.source_slug!r}")
        if not self.source_section.strip():
            raise ValueError("source_section must not be empty")
        if not self.excerpt.strip():
            raise ValueError("excerpt must not be empty")


def _quote_excerpt(excerpt: str) -> str:
    lines = excerpt.strip("\n").splitlines()
    rendered: list[str] = []
    in_display_math = False

    for line in lines:
        stripped = line.strip()
        if not in_display_math:
            rendered.append(f"  > {line}")
            if stripped == "$$":
                in_display_math = True
            continue

        rendered.append(f"  {line}")
        if stripped == "$$":
            in_display_math = False

    return "\n".join(rendered)


def render_card(card: EvidenceCard) -> str:
    header = (
        f"- `{card.evidence_id}` {card.use_label.strip()} — {card.short_label.strip()} "
        f"([prepared markdown](../sources/papers/{card.source_slug}.md), "
        f"{card.source_section.strip()}): ^{card.evidence_id}"
    )
    return f"{header}\n{_quote_excerpt(card.excerpt)}"


def render_pack(cards: list[EvidenceCard], *, include_heading: bool = True) -> str:
    if not cards:
        raise ValueError("at least one evidence card is required")
    body = "\n\n".join(render_card(card) for card in cards)
    if include_heading:
        return f"## Evidence Pack\n\n{body}"
    return body


def card_from_mapping(data: dict[str, Any]) -> EvidenceCard:
    evidence_id = data.get("evidence_id", data.get("id"))
    return EvidenceCard(
        evidence_id=str(evidence_id),
        use_label=str(data["use_label"]),
        short_label=str(data["short_label"]),
        source_slug=str(data["source_slug"]),
        source_section=str(data["source_section"]),
        excerpt=str(data["excerpt"]),
    )


def cards_from_json(path: Path) -> list[EvidenceCard]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    raw_cards = data.get("cards") if isinstance(data, dict) else data
    if not isinstance(raw_cards, list):
        raise ValueError("input JSON must be a list or an object with a cards list")
    return [card_from_mapping(card) for card in raw_cards]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render canonical llm-wiki Evidence Pack markdown from structured parameters."
    )
    parser.add_argument("--input", type=Path, help="JSON file containing a cards list")
    parser.add_argument("--no-heading", action="store_true", help="omit the ## Evidence Pack heading")
    parser.add_argument("--id", dest="evidence_id", help="single-card evidence id, e.g. E1")
    parser.add_argument("--use-label", help="single-card use label, e.g. Method")
    parser.add_argument("--short-label", help="single-card short label")
    parser.add_argument("--source-slug", help="single-card prepared source slug")
    parser.add_argument("--source-section", help="single-card source section label")
    parser.add_argument("--excerpt", help="single-card exact source excerpt")
    parser.add_argument("--excerpt-file", type=Path, help="read single-card excerpt from a UTF-8 text file")
    return parser


def _single_card_from_args(args: argparse.Namespace) -> EvidenceCard:
    excerpt = args.excerpt
    if args.excerpt_file is not None:
        excerpt = args.excerpt_file.read_text(encoding="utf-8")
    required = {
        "--id": args.evidence_id,
        "--use-label": args.use_label,
        "--short-label": args.short_label,
        "--source-slug": args.source_slug,
        "--source-section": args.source_section,
    }
    missing = [flag for flag, value in required.items() if not value]
    if not excerpt:
        missing.append("--excerpt or --excerpt-file")
    if missing:
        raise ValueError(f"missing required single-card arguments: {', '.join(missing)}")
    return EvidenceCard(
        evidence_id=args.evidence_id,
        use_label=args.use_label,
        short_label=args.short_label,
        source_slug=args.source_slug,
        source_section=args.source_section,
        excerpt=excerpt,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.input is not None:
            cards = cards_from_json(args.input)
        else:
            cards = [_single_card_from_args(args)]
        print(render_pack(cards, include_heading=not args.no_heading))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
