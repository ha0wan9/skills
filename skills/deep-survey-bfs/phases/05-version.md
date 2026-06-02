# Phase: version

Use when new evidence (new papers, new datasets, new model weights,
empirical experiments) should be folded into an existing `survey.md`
without rewriting prior content.

## Steps

1. Read the existing `survey.md`, `claims.jsonl`, `paper_index.md`. Load
   `references/claims-discipline.md`.

2. Ingest the new evidence. Decide its kind:
   - **New paper(s)** → add `P00N` rows to `paper_index.md`, score on the
     rubric. If they fill a gap or open a new sub-route, run a mini
     gap-audit. If they invalidate prior claims, mark which.
   - **New dataset / benchmark** → add a row to the dataset table; if it
     re-orders the comparative ranking from §4 or §6, mark the affected
     ranking with a `(vN superseded)` note.
   - **New model weights / open-source release** → add a row to
     `paper_index.md` even if no new paper, with a note marking it as
     "weights-only artifact". This unlocks empirical analyses (see next).
   - **Empirical experiment** (e.g., SVD weight analysis, latency
     benchmark, reproduction study) → add as a delta section, not a
     paper row. Reference any underlying papers via their existing IDs.

3. Decide section placement:
   - Pure additions → new sub-section (e.g., §10.7 "Weight spectrum
     analysis (vN added)") with a clear `(vN added)` marker in the
     heading.
   - In-place updates to prior sections → minimal edits, marked with
     `(vN supplement)` inline. Do not delete prior text.
   - Superseded prior claims → mark the prior claim with
     `(vN: superseded by Cxxx)` and write the corrected claim alongside.
     Do not silently delete.

4. Update `claims.jsonl`:
   - New claim rows for new evidence.
   - Set superseded prior claim rows' status to `superseded`, pointing
     to the new claim ID.

5. Update the version footer:
   ```
   *Survey vN. Delta from v(N-1):
    - new section §X.Y (...)
    - supplemented §A.B with (...)
    - superseded claim Cxxx (now Cyyy)*
   ```

6. Re-run `python3 skill/scripts/claims_validate.py claims.jsonl
   survey.md`. Confirm zero broken claim references; superseded claims
   should still resolve (they remain in the JSONL with status set).

## Versioning Discipline

- **Section anchors are stable.** v1's `§5.4` stays at `§5.4` in v2 even if
  v2 supplements it. Cross-references from elsewhere must keep working.
- **Paper IDs are immutable.** Once `P004` is assigned, it stays `P004`
  forever; new papers get new IDs.
- **Major rewrites mean a new survey-id, not a new version.** If the
  research question itself shifts, frame a new survey and link from the
  old one as `superseded by <new-survey-id>`.

## Sub-Question Addition (frame amendment)

A new sub-question normally means a *new survey* (the frame invariant). But
when the user explicitly asks to widen an existing survey by one sub-question
and it stays within the original research question, handle it as a
**changelogged frame amendment + scoped version update** rather than a silent
edit or a full new survey. Procedure (validated on a 13-SQ run that added SQ13
post-v1):

1. **Amend `index.md`, visibly.** Append the new `SQ<k>` to the Sub-Questions
   list and the Active Evidence Dimensions table, tagged `(vN added, <date>)`,
   with a one-line note that it is an explicit amendment. Add a changelog row.
   Never renumber existing SQs.
2. **Run a *scoped* gap audit — new cells only.** Search (fan out if needed) to
   fill just the new SQ's active cells; do not re-audit the whole matrix. Cross-
   tag any *existing* papers that also answer the new SQ (union their SQ tags;
   see the cross-tag non-double-count rule in `references/taxonomy-revision.md`).
3. **Append-only IDs and claims.** New papers get the next `P` IDs; new claims
   the next `C` IDs. Existing IDs are immutable.
4. **Delta synthesis.** Add a new taxonomy route, deep-dive subsection(s), a
   §12 Q&A entry for the new SQ, and a reading-list line — all marked
   `(vN added)`. Keep every prior section anchor stable.
5. **Re-check, don't re-frame.** Re-run `coverage_check.py` (new cells should
   close) and `bias_audit.py`. This does not consume an audit-round from the
   4-round cap (it is a version update).

## Version vs the Round Cap

The 4-round cap in `03-roundN.md` governs **audit-gated gap rounds** only.
`version` additions — new evidence, user-directed additions, bias/weak-cell
hardening, sub-question additions — are **unbounded** and do **not** reopen the
gap audit (which already passed). Label them as version rounds in the changelog
(e.g. "v4 / Round 5, version") so the distinction stays legible. A survey can go
through many version updates after its audit passes; that is expected for a
long-running topic, not a sign the audit was wrong.

## Hand Off

Set status to `vN-shipped` with the version footer rendered. Output the
delta summary so the user can review only what changed.
