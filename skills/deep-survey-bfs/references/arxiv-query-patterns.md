# arXiv Query Patterns

## Contents

- [Why Query Design Matters](#why-query-design-matters)
- [Field Specifiers](#field-specifiers) — `ti:` `abs:` `au:` `cat:` `all:`
- [Query Templates by Intent](#query-templates-by-intent) — T1-T7
- [Combining Filters](#combining-filters) — AND / OR / NOT
- [Sort Order Trade-offs](#sort-order-trade-offs)
- [Worked Examples](#worked-examples) — what each pattern returns
- [Anti-Patterns](#anti-patterns)

## Why Query Design Matters

The first iteration of this skill used `all:<terms>` for breadth searches.
`all:` matches the term in any indexed field (title, abstract, comments,
authors, MSC class, journal ref) and treats spaces as OR-ish, returning
huge noisy result sets sorted by recency. A query like
`all:stereo matching` returns mostly recent papers tangentially mentioning
either word.

The fix is intent-driven query design: pick the **narrowest** field that
still captures the relevant papers, then widen only when the narrow query
returns too few hits.

## Field Specifiers

| Specifier | Matches | Use for |
|---|---|---|
| `ti:` | title only | high precision; topic-defining work |
| `abs:` | abstract | medium precision; deployment claims, dataset usage |
| `au:` | author | follow-up reads, citation BFS |
| `cat:` | arXiv category | scope filter (cs.CV, cs.LG, eess.SP, etc.) |
| `all:` | any field | last resort; expect noise |

Quoted phrases (`ti:"stereo matching"`) match the exact phrase, not the
unordered terms. Use quotes whenever you mean the phrase.

## Query Templates by Intent

### T1. Topic-defining work (high precision)

```
ti:"<exact topic phrase>" AND cat:<category>
```

Example: `ti:"stereo matching" AND cat:cs.CV` — returns papers whose
title contains the literal phrase. Misses papers using synonyms; combine
with T2 to widen.

### T2. Topic + technique (compound title)

```
ti:<topic> AND ti:<technique>
```

Example: `ti:foundation AND ti:stereo` — finds "FoundationStereo",
"DEFOM-Stereo", "Stereo-Foundation-...", regardless of order.

### T3. Topic in title + qualifier in abstract

```
ti:<topic> AND abs:<qualifier> AND cat:<category>
```

Example: `ti:stereo AND abs:TensorRT AND cat:cs.CV` — papers where
"stereo" is the title topic and the abstract mentions TensorRT (good
for finding deployment-focused work without flooding on TRT papers in
other domains).

### T4. Author follow-up

```
au:<lastname> AND cat:<category>
```

Example: `au:Lipson AND cat:cs.CV` — list a known author's recent CV
work, helpful for citation BFS when keyword search saturates.

### T5. Time window filter

Append `AND submittedDate:[YYYYMMDDhhmm+TO+YYYYMMDDhhmm]`. Use
`submittedDate` not `lastUpdatedDate` for first-submission semantics.

```
ti:"stereo matching" AND submittedDate:[202001010000+TO+202612312359]
```

### T6. Citation-style enumeration

Use Semantic Scholar's citation graph instead of arXiv for forward/back
citation traversal. arXiv has no native citation field. See
`source-coverage.md` for the Semantic Scholar recipe.

### T7. Vendor / non-paper pivot (deployment claim hunt)

When the targeted claim is **deployment-side** (TensorRT engine ms,
Jetson FPS, INT8 quant, ONNX export, edge port) and arXiv returns 0
useful hits, **stop searching arXiv** and pivot to non-paper sources.
This is the most common failure mode of arxiv-only surveys: deployment
numbers don't live in paper abstracts.

Pivot order:

1. **GitHub repo READMEs** of the indexed models. Search for the
   keyword in the README and any `readme_jetson.md` / `deployment.md`
   sub-doc.
2. **NVIDIA developer blog** (`developer.nvidia.com/blog/...`) for
   well-known academic models — NVIDIA sometimes publishes canonical
   TensorRT timings.
3. **Qualcomm AI Hub model zoo** for mobile-targeted variants.
4. **Project pages** linked from each paper's first page.
5. **GitHub Issues** in the repos — authors often disclose latency
   numbers in issue replies that didn't make the README.

For each pivot source, record the URL and (if applicable) the commit
SHA / page version date in the claim's `notes` field; deployment
numbers can be re-tuned on every repo update.

When this pivot produces nothing for several models, that is itself a
finding — record "TRT latency not publicly disclosed" in the survey's
open-challenges section. Do not fabricate by combining a relative
claim ("6× speedup") with another paper's absolute number.

### Anti-pattern reminder

**Searching arXiv for `abs:TensorRT` or `abs:Jetson` for stereo
matching returned 0 hits across three different keyword combinations
in a real Round 2.** This is by design: deployment claims are not in
paper abstracts. T7 pivot is the right move, not "search harder on
arXiv".

## Combining Filters

- **AND**: both conditions must hold (default for whitespace inside the
  query is OR-ish — always be explicit with `+AND+`).
- **OR**: at least one — `(ti:X+OR+ti:Y)`. Wrap in parentheses.
- **NOT**: exclude — `ti:stereo+ANDNOT+ti:audio` to filter out audio
  stereo papers.

When mixing AND/OR, parenthesize aggressively. arXiv API parses
left-to-right without standard precedence.

## Sort Order Trade-offs

| Sort | Behavior | When to use |
|---|---|---|
| `relevance` | arXiv's relevance ranking (term frequency–like) | breadth searches; recommended default |
| `submittedDate&sortOrder=descending` | newest first | sanity-check on what's recent |
| `submittedDate&sortOrder=ascending` | oldest first | tracing the start of a thread |

If `relevance` returns junk, it usually means the query was too broad
(see Anti-Patterns).

## Worked Examples

For the stereo-matching-edge-fm survey:

| Intent | Query | Result quality |
|---|---|---|
| Stereo matching as a topic | `ti:"stereo matching" AND cat:cs.CV` | high precision; returned RAFT-Stereo, IGEV-Stereo, FoundationStereo, etc. |
| Stereo + foundation | `ti:foundation AND ti:stereo` | high precision; returned FoundationStereo, DEFOM-Stereo, "Playing to VFM Strengths", "All-in-One VFM Stereo" |
| Stereo + edge HW | `abs:stereo AND abs:Jetson` | medium precision; returned StereoVoxelNet, embedded-GPU stereo papers, plus some SLAM noise |
| Mamba stereo | `ti:stereo AND ti:mamba` | sparse but precise (1 hit: DenVisCoM) — confirms Mamba-stereo gap |
| Anti-example | `all:stereo matching` | low precision; recency-sorted noise dominates |

## Anti-Patterns

- **Bare `all:` searches**: always returns recency-sorted noise.
- **Single-word `ti:`**: `ti:stereo` matches any "stereo" paper including
  audio stereo, 3D stereo vision (image), and stereoselectivity in
  chemistry. Always pair with category or another `ti:` term.
- **Forgetting `cat:`**: cross-domain term ambiguity (e.g., "stereo" in
  chemistry, "transformer" in electrical engineering).
- **Unquoted phrases**: `ti:stereo matching` may match either `ti:stereo`
  alone OR `ti:matching` alone depending on tokenizer. Always quote
  multi-word phrases.
- **Date-only queries**: `submittedDate:[2024+TO+2026]` with no topic
  filter returns all of recent arXiv. Always pair with a topic.
