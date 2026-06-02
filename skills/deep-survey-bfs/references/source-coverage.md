# Source Coverage

## Contents

- [Why Multi-Source](#why-multi-source) — what each source uniquely tells you
- [arXiv](#arxiv) — primary breadth source
- [OpenReview](#openreview) — peer-review status and reviewer signal
- [DBLP](#dblp) — canonical venue lookup
- [Semantic Scholar](#semantic-scholar) — citation count and influence
- [Search Order](#search-order) — recommended sequencing
- [Anti-Patterns](#anti-patterns) — what each source cannot do

## Why Multi-Source

No single source covers all the signals that determine a paper's place in a
survey. The "preprint" label trap is the canonical failure: arXiv shows
recent work but cannot tell you whether the paper has been peer-reviewed,
withdrawn, or superseded. OpenReview answers that. DBLP authoritatively
maps preprint to venue. Semantic Scholar gives citation-based influence.

A paper that is `arXiv 2024 preprint` per arXiv may be `NeurIPS 2024 main
conference, accepted with score 7.5/8` per OpenReview and `cited 87 times`
per Semantic Scholar. The full picture matters for star rating and for
deciding which version to reference.

## arXiv

Primary breadth source for any technical topic published since ~2020.

- **API**: `arxiv.org/find` with category filter (cs.CV, cs.LG, eess.SP,
  q-bio.NC, etc.). Web UI is acceptable for ad-hoc searches; the API is
  better for systematic listing.
- **Query patterns**:
  - Topic + year filter: `cat:cs.CV AND ti:"stereo matching" AND submittedDate:[2020 TO *]`
  - Author lookup: `au:"Jiang" AND cat:cs.LG` for follow-up reads
  - Cite-trace: arXiv does not have native citation graph; defer to Semantic Scholar
- **Read pattern**: title + abstract + section headings + figure captions
  for inclusion decisions. Title-only triggers false positives.
- **Caveats**:
  - arXiv version is not authoritative; always cross-check OpenReview/DBLP
  - Withdrawn papers stay listed; check status field
  - Workshop papers and main-conference papers can have separate arXiv IDs

## OpenReview

Peer-review status, reviewer scores, decision history.

- **Coverage**: ICLR, NeurIPS, ICML (recent years), TMLR, plus many
  workshops. CVPR/ICCV/ECCV/AAAI are not on OpenReview — defer to DBLP.
- **Why query**:
  - Convert `arXiv preprint` to `accepted at <venue>` (or rejected/withdrawn)
  - Reviewer scores indicate how the field rates the work
  - Discussion threads occasionally reveal reproducibility issues
- **Signals to record in the index**:
  - Decision (accept / reject / withdrawn / under-review)
  - Average reviewer score
  - Discussion length (a controversial paper has a long thread)

## DBLP

Authoritative venue + author bibliography.

- **Use cases**:
  - Confirm "did this paper actually appear at NeurIPS 2024 main, or only at
    a workshop?"
  - Build an author's track record (key for assessing authority dimension
    of the rubric)
  - Disambiguate similar names
- **Limitations**: indexes formal publications, not preprints; lag of 1-2
  months after publication

## Semantic Scholar

Citation count, influence, and citation graph traversal.

- **Use cases**:
  - Influence signal for the rubric's `authority` dimension
  - Citation BFS: from a seminal paper, find papers that cite it for the
    same sub-question (use during Round N when keyword search is exhausted)
  - "Highly Influential Citations" filter cuts through citation count
    inflation
- **Caveats**:
  - Citation count favors older papers; normalize by years-since-publication
    when comparing across years
  - The API is rate-limited; batch lookups when possible

## Search Order

For Round 1:

1. arXiv keyword search → produces 30-50 candidates
2. For each candidate, OpenReview lookup if arXiv ID has a known venue
3. DBLP for venue confirmation on the survivors
4. Semantic Scholar for citation count of survivors

For Round N (gap-driven):

1. Reformulate keywords specific to the gap
2. Citation BFS from existing ★★★ papers in adjacent cells
3. OpenReview venue listings (browse the year's accepted papers in the
   relevant track)

## Anti-Patterns

- **arXiv-only surveys** miss venue and peer-review signal; produce a list
  of preprints that may include withdrawn or rejected work
- **Google-Scholar-only surveys** mix genuine peer-reviewed work with
  predatory journals indistinguishably; not a substitute for the four
  sources above
- **Citation-count-only ranking** systematically biases against recent work
  and against critical/limitations papers (which get cited less than
  enthusiastic ones)
- **Treating a negative finding as settled fact**, especially for active
  industrial labs. "This is a single paper / there is no successor / there is
  no vN" is a *negative* claim, and a clean search miss is weak evidence for it.
  Fast-moving industrial groups (Meta FAIR, Google DeepMind, the Allen
  Institute, OpenAI, etc.) ship successors and "vN" follow-ups on a
  quarterly cadence that arXiv/Semantic Scholar/DBLP index with lag. **Before
  asserting "no successor/no series," check the lab's own publications page and
  blog/release notes**, not just preprint aggregators — and mark the conclusion
  `confidence: low` if you can't positively confirm absence. Real failure mode:
  a search pass concluded "TRIBE is a single paper, no series"; the lab had
  already shipped **TRIBE v2** (announced on the lab blog), which the aggregators
  hadn't surfaced. A reader caught it. Negative claims about active labs need
  the lab's primary channel, or a low-confidence hedge.
