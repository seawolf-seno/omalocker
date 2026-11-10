# OmaLocker plan

**Goal.** Every person at Pacifica (teacher, student, staff) has one folder of Markdown
files, `~/Locker`, that holds their school life: classes, people, activities, writing,
growth, and pathway. Obsidian (or any editor) shows the links between them. Our other
apps read and write into it through small, named contracts, so it becomes each person's
main storage.

**Principle.** Obsidian is the app. OmaLocker is the format plus small glue (`omalocker`
CLI, Python stdlib like Omacanvas). Remove before adding: no new GUI until the files prove
they're not enough.

## How connections work

- One note per thing (a class, a person, a club, an idea, a day, a piece of work).
- Links are `[[wikilinks]]` in text and in frontmatter properties, so Obsidian's graph,
  backlinks and Bases (core plugin, table views) see them with no community plugins.
- **Ideas are the bridge between classes.** OmaMastery's `ideas.toml` ties each course's
  core ideas to a shared *joint* ("One Body, Many Members"). Each joint becomes a note in
  `Ideas/`, so Physics and AP CS link through the joints they share, and a student's work,
  journal and activities can link to the same joints.
- Apps own a marked block, never the person's words:
  `<!-- omalocker:<source> -->` … `<!-- /omalocker:<source> -->`. Re-running an import
  rewrites only that block.

Format details: `docs/format.md`.

## Connections to test

| Project | Flow | Contract | Test |
|---|---|---|---|
| **OmaMastery** (`~/Classes`) | Classes → Locker | `class.toml`, `ideas.toml`, `plan.toml` → `Classes/<class>.md`, `Ideas/<joint>.md` | Sample classes import; links resolve; `roster.toml`/`mastery.csv` never read for real classes |
| **OmaClass** (Veyon) | Classes → Locker | `room` in `class.toml` → class note property | Room shows on class note |
| **pacos** | installs/creates | `omalocker` package; `pacos-session-setup` creates `~/Locker` from `template/`; `~/Locker` in `writable`; locked `.obsidian/` (no community plugins) | VM: teacher and student (`beno29`) get a Locker; student can't enable plugins |
| **PacTerminus** | Terminus → Locker | `~/.local/share/omaterminus/complete` → `Pathway/Milestones.md` entry | VM: finish quest → milestone appears. Bonus: a quest step that teaches `cd ~/Locker` |
| **Omawrite + Omacanvas turn-in** | both ways | Omawrite saves to `Work/<class>/`; `turnin.py` submits from there and sets `status: turned-in` | Fictional test account submits a Locker file |
| **Omadesmos** | Desmos → Locker | Saved graph links pasted into Work notes | Manual, low priority |
| **Canvas** | Canvas → Locker | Reuse OmaMastery setup (keyring token): assignments → `Work/<class>/` stubs with due dates | Sandbox course only |
| **Formation Pathways** | FP → Locker (one way) | Student's own signed pathway → `Pathway/Pathway.md`; teacher person notes link to FP page, never copy observations | **Staging DB, fictional students only.** Blocked for real data on consent policy |
| **starter-template / GitHub** | Locker → backup | Locker is a git repo; optional private remote | Backup + restore on a fresh VM |
| **Pacifica OS / Systems Map** | docs | Milestone + "where each person's data lives" diagram | Updated when a phase lands |

`make test-connections` (Phase 1) builds a fictional school in a temp `HOME` (sample
`~/Classes`, a Terminus marker, an FP staging export), runs every import, then
`omalocker doctor`: valid frontmatter, no broken links, no real names (checked against a
deny-list of fixture rules, not a roster).

## Phases

**0. Format (this week).** `docs/format.md` + `template/` vault. Open it in Obsidian; check
graph and backlinks feel right with ~20 fictional notes. Seno decides folder names.

**1. Teacher locker on seno's machine.** `omalocker init`, `omalocker import classes`,
`omalocker doctor`, `make test-connections`. Decide whether `~/Classes` moves to
`~/Locker/Classes` (recommended; OmaMastery gets a configurable root, `~/Classes` stays as
a symlink so nothing breaks).

**2. Student locker in the pacos VM.** Package, `/etc/skel` or session-setup creation,
locked Obsidian config, Terminus milestone, Omawrite save location, turn-in from the
Locker. Students get Obsidian only after PacTerminus (fits the tier model).

**3. Outside connections (fictional data).** Canvas sandbox import, FP staging export,
git backup/restore.

**4. Pilot.** Seno + one class, after the decisions below. Measure: can a student find
"everything about this week" in under a minute?

## Decisions for seno

1. **Locker vs. "one database."** Recommended: the Locker is the source of truth for a
   person's own notes and work; the school database holds shared, consented records and
   pushes copies *into* Lockers. Nothing flows from a Locker to the school automatically.
   (Systems Map needs this added.)
2. **Move `~/Classes` into `~/Locker`?** Recommended yes, with a symlink.
3. **Backup.** Recommended: git to a private repo per person once the consent policy allows;
   until then, local only (pacos disk encryption covers device theft, not loss). No Obsidian
   Sync or third-party cloud for real student data.
4. **Teacher notes about students.** `People/` in a teacher's Locker are education records
   (FERPA). Same rules as `roster.toml`: owner-only files, agents never open them for real
   students, never committed or synced. Confirm with leadership.
5. **Who can see a student's Locker?** It's on a school machine. Proposal: the student
   only, unless they share a note. Needs leadership sign-off before Phase 4.
6. **Obsidian licensing for a school.** Check current terms before rollout (verify; don't
   assume).

## Risks

- `.obsidian/` can load plugin code. For students it's part of the managed config, not
  `writable` (pacos rule: nothing read as code at login is writable).
- Free-form files drift. `omalocker doctor` keeps frontmatter valid; imports never touch
  the person's own text.
- Single point of failure (only seno). Keep the format simple enough that a person with
  only a text editor can use it.
