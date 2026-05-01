#!/usr/bin/env python3
"""Validate claims.jsonl integrity and confirm survey.md citations resolve.

Checks:
  1. claims.jsonl parses; required fields present per row.
  2. Every paper_id in claims resolves to a row in paper_index.md.
  3. Every (Pxxx) reference inside survey.md resolves to a paper row.
  4. Every Cxxx reference inside survey.md resolves to a claim row.
  5. status='superseded' rows have a superseded_by that resolves to an
     active claim.

Usage:
  python3 claims_validate.py <claims.jsonl> <survey.md> [paper_index.md]

If paper_index.md is omitted, it is inferred as <survey-dir>/paper_index.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = ("claim_id", "kind", "paper_id", "section")


def parse_paper_ids(paper_index_text: str) -> set[str]:
    ids: set[str] = set()
    for raw in paper_index_text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if re.match(r"^P\d{3,5}$", first):
            ids.add(first)
    return ids


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: claims_validate.py <claims.jsonl> <survey.md> [paper_index.md]",
              file=sys.stderr)
        return 2
    claims_path = Path(argv[1])
    survey_path = Path(argv[2])
    paper_index_path = (
        Path(argv[3]) if len(argv) >= 4 else survey_path.parent / "paper_index.md"
    )

    errors: list[str] = []

    # Load paper IDs
    if not paper_index_path.is_file():
        errors.append(f"paper_index.md not found at {paper_index_path}")
        paper_ids: set[str] = set()
    else:
        paper_ids = parse_paper_ids(paper_index_path.read_text(encoding="utf-8"))

    # Load claims
    claims: dict[str, dict] = {}
    if not claims_path.is_file():
        errors.append(f"claims.jsonl not found at {claims_path}")
    else:
        with claims_path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"claims line {line_no}: invalid JSON ({exc})")
                    continue
                cid = obj.get("claim_id", "")
                if not cid:
                    errors.append(f"claims line {line_no}: missing claim_id")
                    continue
                if cid in claims:
                    errors.append(f"claims line {line_no}: duplicate claim_id {cid}")
                claims[cid] = obj
                for field in REQUIRED_FIELDS:
                    if not obj.get(field):
                        errors.append(f"{cid}: missing required field {field}")
                if obj["paper_id"] not in paper_ids:
                    errors.append(
                        f"{cid}: paper_id {obj['paper_id']} not in paper_index.md"
                    )
                if not obj.get("quote") and not obj.get("table_ref") and not obj.get("figure_ref"):
                    errors.append(f"{cid}: must have quote, table_ref, or figure_ref")
                if obj.get("status") == "superseded":
                    sb = obj.get("superseded_by")
                    if not sb:
                        errors.append(f"{cid}: status='superseded' requires superseded_by")

    # Verify superseded chain after all claims loaded
    for cid, obj in claims.items():
        if obj.get("status") == "superseded":
            sb = obj.get("superseded_by")
            if sb and sb not in claims:
                errors.append(f"{cid}: superseded_by {sb} does not exist")
            elif sb and claims[sb].get("status") == "superseded":
                errors.append(f"{cid}: superseded_by {sb} is itself superseded")

    # Verify depends_on references and report eligible confidence promotions
    promotion_hints: list[str] = []
    for cid, obj in claims.items():
        deps = obj.get("depends_on")
        if not deps:
            continue
        if not isinstance(deps, list):
            errors.append(f"{cid}: depends_on must be a list of claim_ids")
            continue
        for dep in deps:
            if dep not in claims:
                errors.append(f"{cid}: depends_on target {dep} does not exist")
                continue
            if claims[dep].get("status") == "superseded":
                errors.append(
                    f"{cid}: depends_on target {dep} is superseded; update or remove the dependency"
                )
        # Propagation hint: if this claim is confidence=medium and all its
        # active deps are now confidence=high, suggest promotion.
        if obj.get("confidence") == "medium" and deps and not errors:
            dep_confidences = [claims[d].get("confidence") for d in deps if d in claims]
            if dep_confidences and all(c == "high" for c in dep_confidences):
                promotion_hints.append(
                    f"{cid}: all depends_on targets are confidence=high; "
                    f"consider promoting {cid} from medium to high"
                )

    # Check survey.md references
    if survey_path.is_file():
        survey_text = survey_path.read_text(encoding="utf-8")
        for ref in re.findall(r"\(P\d{3,5}\b", survey_text):
            pid = ref.lstrip("(")
            if pid not in paper_ids:
                errors.append(f"survey.md references unknown paper: {pid}")
        for ref in re.findall(r"\(C\d{3,5}\b", survey_text):
            cid = ref.lstrip("(")
            if cid not in claims:
                errors.append(f"survey.md references unknown claim: {cid}")
    else:
        errors.append(f"survey.md not found at {survey_path}")

    if errors:
        print(f"validation failed with {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"ok: {len(claims)} claims, {len(paper_ids)} papers, all references resolve")
    if promotion_hints:
        print(f"\nconfidence-promotion hints ({len(promotion_hints)}):")
        for h in promotion_hints:
            print(f"  - {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
