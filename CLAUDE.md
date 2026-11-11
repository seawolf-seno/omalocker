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
- 2026-11-10: `omalocker mastery`: per-class graph (counts per level, no names) as
  `Mastery/` notes + offline `graph.html`; idea/joint level = each student's lowest. It is
  the only command that reads `mastery.csv` (agents still never open it).
- 2026-11-10: `omalocker backup` / `restore` (restic, settings in
  `/etc/omalocker/backup.toml`, key passed as a file only); hourly `--if-due` systemd timer
  in `systemd/`; doctor warns when a backup is missing or late. Tests need restic
  (`OMALOCKER_RESTIC=...`; skipped without it). Tests clear XDG_* and OMALOCKER_* env.
- 2026-11-10: `omalocker views` (student Lockers only): per-audience views in
  `~/.local/state/omalocker/views/` with `view.json` (`as_of`); rebuilt from scratch each run;
  doctor fails on a view holding a note its audience can't see. Not pushed anywhere yet.
- 2026-11-10: viewer started: `viewer/omalocker-viewer` (stdlib, SQLite, staging takes test
  emails only), `omalocker push`; docs in `docs/viewer.md`. Sign-in = one-time links printed
  by admin; family/custody records by `grant`. Tests: `tests/test_viewer.py` + connections.
- 2026-11-10: graduation: `omalocker graduate --to DIR` (zip for the student, then no push or
  backup; `graduated.json` in state), `omalocker-viewer graduate EMAIL [--yes]` (deletes
  student, views, grants, token, family logins with no other student). IT deletes backups.
- 2026-11-10: viewer access log (`audit` table, `omalocker-viewer audit`): opens, refusals,
  sign-ins, pushes, admin commands. Graduation deletes the student's entries and blanks
  deleted people's emails (to confirm against FERPA 99.32).
- Scope (seno, 2026-11-10): work only in this repo; don't change sibling repos.
- Next: seno opens `fixtures/sample-locker` in Obsidian (Phase 0); open decisions in
  `docs/plan.md` (backup key, where the viewer runs, parent sign-in, custody records);
  viewer: emailed links, records import (after Mr. Eno answers); then pacos packaging. Notes about classmates are in no view (seno, 2026-11-10).
