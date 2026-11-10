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

## Status
- 2026-11-09: repo created; plan (`docs/plan.md`), format v0 draft, template vault. No code.
- Next: seno answers the decisions in `docs/plan.md`, then Phase 0/1 (`init`, `import
  classes`, `doctor`, `make test-connections`).
