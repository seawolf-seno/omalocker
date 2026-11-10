# omalocker

OmaLocker: each person's school life as Markdown in `~/Locker`, viewed in Obsidian. Part of
the school dev platform initiative (see `~/.claude/CLAUDE.md`). Siblings: `../omamastery`
(`~/Classes`), `../pacos`, `../pacterminus`, `../omacanvas`, `../formation-pathways`.

- Obsidian is the app; this repo is the format (`docs/format.md`), `template/`, and later a
  small `omalocker` CLI (Python stdlib). No GUI until files prove insufficient.
- Imports write only inside their own `<!-- omalocker:<source> -->` block.
- Fictional data only in this repo, fixtures and tests. Real lockers stay on their machine.
- Same agent rules as `~/Classes/AGENTS.md`: never open `roster.toml`, `mastery.csv`, or
  notes about real students.

- **Each person's device is the source of truth** (seno, 2026-11-10). Only views (filtered on
  the device, per audience) and the existing grades pipe leave it. See `docs/plan.md`.
- Mastery graph is built from structured files, no AI. Graphify only on curriculum files.

## Status
- 2026-11-09: repo created; plan, format v0 draft, template vault. No code.
- 2026-11-10: plan revised: device = truth, per-audience views (FP as viewer host,
  proposed), mastery graph, Obsidian kept.
- Next: seno's open decisions in `docs/plan.md` (backup, FERPA, viewer host); Phase 0/1.
