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

## Hand Off

Set status to `vN-shipped` with the version footer rendered. Output the
delta summary so the user can review only what changed.
