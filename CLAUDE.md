# omalocker

OmaLocker: each person's school life as Markdown in `~/Locker`, viewed in Obsidian. Part of
the school dev platform initiative (see `~/.claude/CLAUDE.md`). Siblings: `../omamastery`
(`~/Classes`), `../pacos`, `../pacterminus`, `../omacanvas`. **Not** connected to
`../formation-pathways`: OmaLocker has its own viewer app (seno, 2026-11-10).

- Obsidian is the app; this repo is the format (`docs/format.md`), `template/`, and a small
  `omalocker` CLI (`bin/omalocker`, Python stdlib, single file). No GUI until files prove insufficient.
- Imports write only inside their own `<!-- omalocker:<source> -->` block and the properties
  they own (`docs/format.md`).
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
- 2026-11-10: seno decided backup, parent access, custody, graduation; viewer is OmaLocker's
  own app, fully separate from FP.
- 2026-11-10: Phase 0 sample Locker (`fixtures/sample-locker`); format decisions in
  `docs/phase0.md` (joint type, milestones one note each, `share` always a list).
- 2026-11-10: Phase 1 CLI `bin/omalocker` (stdlib): `init [--role] [--move-classes]`,
  `import classes`, `doctor`. Tests: `make test`, `make test-connections`
  (fixture `fixtures/classes`, fictional). Import reads only class/ideas/plan.toml.
- Next: seno opens `fixtures/sample-locker` in Obsidian (Phase 0); `omalocker mastery`;
  run init/import on seno's machine; open decisions in `docs/plan.md`.
