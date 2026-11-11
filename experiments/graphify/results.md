# Results (2026-11-10)

Graphify 0.9.106, `graphify extract syllabi --backend claude-cli`, then
`graphify cluster-only syllabi --backend=claude-cli`. No API keys were set, so nothing
else could be chosen. Four fictional syllabi: 39,733 tokens in, 8,931 out (Claude
subscription). Output: 32 concepts, 47 links, 5 communities, 3 hyperedges (groups of
concepts that belong together).

## Score against `answer-key.md`

| Planted joint | Courses | Found? | How |
|---|---|---|---|
| Argument from evidence | Bio, Eng, Geo, Theo | **Yes, whole** | hyperedge of all four: "Every course requires claims backed by evidence and explicit reasoning" (0.85) |
| Care for creation | Bio, Eng, Theo | **Yes, whole** | hyperedge of all three: "Caring for a local place/environment across subjects" (0.8) |
| Pattern, symmetry and form | Bio, Eng, Geo | **Yes, whole** | hyperedge of all three: "Symmetry, repeating patterns and ratios" (0.7) |
| Systems and feedback | Bio, Theo | **Yes, weaker** | links only: "Many members, one body" to homeostasis (0.65) and to predator-prey (0.5, marked ambiguous) |

**Recall: 4 of 4** (three as complete groups). **False joints: 0**: none of the decoys
(cell division, narrative voice, trigonometry, sacraments) was linked to another course.

## What to watch

- **The groups are in the hyperedges and cross-course links, not the communities.**
  Communities mostly came out one per course ("Biology and Living Systems", "Theology and
  Apologetics", ...). Reading only the community list would miss the joints.
- **Boilerplate makes fake links.** The same assessment line in every syllabus ("Not yet,
  Beginning, ...") became one shared "Mastery scale" node that every course references.
  Real syllabi share much more boilerplate (policies, grading, contact info); strip it
  first, or ignore `references` links and keep `semantically_similar_to` /
  `conceptually_related_to` and hyperedges.
- **Teachers' names became concepts.** Fine for staff, but it shows Graphify keeps whatever
  is in the files: curriculum files must hold no student names (`docs/plan.md` rule).
- **This was the easy case.** One author (Claude) wrote syllabi with ideas planted on
  purpose, and the same model family found them. Real syllabi are longer, messier and
  written by different people.
- **Cost scales with text.** ~40k input tokens for four one-page syllabi; long-range plans
  for a whole school would be much more.

## Verdict and next step

Worth trying on real curriculum: it found every planted joint, with no false ones, from
differently worded text. Suggested next step (seno's call, on his machine): run it on two
or three real syllabi or long-range plans with boilerplate removed, and have the teachers
judge the hyperedges. If they hold up, a small `omalocker` step could turn accepted
hyperedges into `joint` notes in `Ideas/`; nothing is built for that yet.
