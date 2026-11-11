# OmaLocker

Each person's school life (classes, people, activities, writing, growth, pathway) as plain
Markdown files in `~/Locker`. Open it in Obsidian to see how everything connects. Pacifica's
other Omarchy apps (OmaMastery, PacTerminus, Omawrite turn-in) read and write into it.
Parents, teachers and advisors see it through OmaLocker's own viewer app, which is separate
from Formation Pathways.

- `template/`: the empty Locker every person starts with (open it in Obsidian to try).
- `docs/format.md`: note types and properties.
- `docs/plan.md`: the build plan and the connections to test.

## Commands (Python stdlib, `bin/omalocker`)

| Command | Does |
|---|---|
| `omalocker init [--role teacher]` | Sets up `~/Locker` from `template/`; never overwrites a note |
| `omalocker init --move-classes` | Moves `~/Classes` (OmaMastery) into `~/Locker/Classes` and leaves a link at `~/Classes` |
| `omalocker import classes` | A note per OmaMastery class, plus its core ideas and joints in `Ideas/`. Reads only `class.toml`, `ideas.toml`, `plan.toml`; rewrites only its own block. Safe to run again |
| `omalocker mastery` | Mastery graph per class: joints → core ideas → objectives, each with how many students are at each level. Writes `Mastery/<class>.md`, a note per objective, and an offline `Mastery/graph.html`; colors Obsidian's graph by level if you haven't set color groups. Reads `mastery.csv` to count; no name reaches a note |
| `omalocker backup [--if-due \| --status]` | Encrypted backup of the whole Locker with restic, to the school storage set in `/etc/omalocker/backup.toml`. A systemd timer (`systemd/`) runs `--if-due` hourly; it backs up every 2 days. See `docs/backup.md` |
| `omalocker restore [--to DIR]` | Restores the newest backup into a missing or empty `~/Locker`, or a new folder. Never writes over notes |
| `omalocker views [--out DIR]` | On a student's Locker: builds each audience's view (parent, advisor, each teacher, each activity leader) in `~/.local/state/omalocker/views/`, filtered by `type`, linked classes/activities and `share`. Private notes, `AGENTS.md` and notes about classmates are never in a view. See `docs/plan.md` |
| `omalocker push` | Builds the views and sends them to the viewer set in `/etc/omalocker/viewer.toml` (https only) |
| `omalocker graduate --to DIR` | Zips the student's whole Locker for them, then stops this device pushing views and making backups. Then the viewer and IT delete the school's copies: `docs/graduation.md` |
| `omalocker doctor` | Checks every note: frontmatter, `type`, `share`, where it lives, blocks, links; and that the backup isn't missing or late. Hides `People/` notes and link targets unless `--show-names` |

## Viewer (`viewer/omalocker-viewer`)

OmaLocker's own app where parents, teachers, advisors and activity leaders open the views
they're allowed to see. One stdlib Python file (SQLite, behind a TLS proxy): one-time
sign-in links, family records with primary custody, grants, a role check on every page, and an access log (`omalocker-viewer audit`).
Staging only for now. See `docs/viewer.md`.

`make test` runs the unit tests (backup tests need `restic`, or `OMALOCKER_RESTIC=/path/to/restic`); `make test-connections` builds a fictional school in a temp
`HOME` and runs every connection built so far.

Status: Phase 1 commands built (init, import classes, mastery, doctor), encrypted backup/restore, per-audience views on the device, a first viewer (staging, fictional people) with an access log, and graduation. Next: emailed sign-in links and family records from the school's records (waiting on Mr. Eno); or packaging in pacos.
