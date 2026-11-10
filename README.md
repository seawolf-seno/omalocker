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
| `omalocker doctor` | Checks every note: frontmatter, `type`, `share`, where it lives, blocks, links. Hides `People/` notes and link targets unless `--show-names` |

`make test` runs the unit tests; `make test-connections` builds a fictional school in a temp
`HOME` and runs every connection built so far.

Status: Phase 1 commands built (init, import classes, mastery, doctor). Next: run them on a real teacher machine.
