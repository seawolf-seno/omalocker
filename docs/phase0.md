# Phase 0: format trial

Sample Locker: `fixtures/sample-locker/` (fictional sophomore "Rowan Teague", 28 notes:
4 classes, 7 people, 2 activities, 4 ideas, 2 journal days, 2 work items, goals,
milestones, one mastery copy, one inbox note). Every note's frontmatter is valid YAML and
every `[[link]]` resolves.

To try it: open `fixtures/sample-locker` as a vault in Obsidian; look at the graph,
backlinks on `Ideas/Systems and feedback`, and a Base over `type`.

## Fixed

- `format.md` still said `Pathway/` holds a Formation Pathways copy and `pathway` notes
  have `source: formation-pathways`. Removed: OmaLocker has no FP connection (decision 7).

## Format questions for seno

1. **Types the format doesn't list.** The template already uses `type: home`; the sample
   needed `mastery` (for `Mastery/<class>.md`) and `inbox`. Add these three?
2. **`AGENTS.md` has no frontmatter**, so it breaks "every note has a type". Give it
   `type: guide`, or exempt it?
3. **Joints.** An `idea` links to its `joint`, but a joint has no type. The sample makes the
   joint an `idea` note with no `joint` property. Keep that, or add `type: joint`?
4. **Milestones: one note or many?** The format gives `milestone` per-entry properties
   (`date`, `source`, `evidence`), but the template has one `Pathway/Milestones.md` list
   that apps append to. Per-milestone notes are easier to filter into views; one list is
   easier to read.
5. **Classmates in a student's Locker.** `People/` in a student Locker will describe real
   students (lab partners, teammates). `AGENTS.md` says agents never open those notes. That
   means an agent can't help with much of a student's own journal. Fine for now?
6. **`share` has two shapes** (`private`, or a list of audiences). Workable, but a single
   list (`share: [private]`) would be simpler for `doctor` and the views to check.

Folder names held up; no changes suggested.
