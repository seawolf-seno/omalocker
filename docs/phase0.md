# Phase 0: format trial

Sample Locker: `fixtures/sample-locker/` (fictional sophomore "Rowan Teague", 29 notes:
4 classes, 7 people, 2 activities, 3 ideas, 1 joint, 2 journal days, 2 work items, goals,
2 milestones, one mastery copy, one inbox note). Every note's frontmatter is valid YAML and
every `[[link]]` resolves.

To try it: open `fixtures/sample-locker` as a vault in Obsidian; look at the graph,
backlinks on `Ideas/Systems and feedback`, and a Base over `type`.

## Fixed

- `format.md` still said `Pathway/` holds a Formation Pathways copy and `pathway` notes
  have `source: formation-pathways`. Removed: OmaLocker has no FP connection (decision 7).

## Decided (seno, 2026-11-10)

1. New types `home`, `mastery`, `inbox`, `guide` are in `format.md`.
2. `AGENTS.md` is `type: guide`, so every note has a type, no exceptions.
3. Joints are their own type, `joint`, in `Ideas/`; ideas link to them with `joint:`.
4. Milestones are one note each in `Pathway/Milestones/`, named `YYYY-MM-DD <name>.md`,
   so views can filter them by property. Replaces the single `Milestones.md` list.
5. Agents still never open `People/` notes about real students, classmates included,
   until the school's AI policy changes.
6. `share` is always a list; `[private]` replaces `private: true` and can't be combined.

Folder names held up. Still to do: open the sample in Obsidian (graph, backlinks, a Base
over `type`) and confirm.
