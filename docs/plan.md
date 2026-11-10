# OmaLocker plan

**Goal.** Every person at Pacifica (teacher, student, staff) has one folder of Markdown
files, `~/Locker`, on their own device. **That folder is the source of truth** for their
school life: classes, people, activities, writing, mastery, pathway. Other people (parents,
teachers, advisors, admin) see a student's Locker through **views** built on the device,
each with only the detail that audience gets.

**Principle.** Plain files on the device; the editor is replaceable. OmaLocker is the format
plus small glue (`omalocker` CLI, Python stdlib like Omacanvas). Remove before adding.

## Who owns what (decided 2026-11-10)

Every record has one owner device. Everyone else gets a copy.

| Record | Owner (source of truth) | Copies go to |
|---|---|---|
| A student's notes, journal, work, goals, activities | Student's device | Views, per the sharing rules |
| Mastery levels, teacher notes about a class | Teacher's device (OmaMastery files) | Student's Locker (levels only), views |
| Course-level grades (transcript) | System of record, **unchanged**: they keep flowing the way they do now | Lockers, read-only |
| Rosters, schedule, Canvas assignments | Canvas / Blackbaud | Lockers, pulled on setup |

Only two things leave a device: the grades pipe that already exists, and views.

## Views: who sees what

The device builds each view by filtering notes on their properties (`class`, `type`,
`share`), then pushes only that view to the viewer host. Nothing outside a view leaves the
device.

| Audience | Default view |
|---|---|
| Student | Everything (it's theirs) |
| Parent / guardian | Course grades, milestones, mastery graph at the core-idea level, pathway. No journal, no notes. |
| Teacher | Their own classes: the student's work and notes tagged with that class, objective-level mastery for that class |
| Advisor / counselor | All classes at the core-idea level, activities, pathway |
| Activity leader | Notes tagged with their activity |
| Admin | Same as parent, plus attendance-type records if added later. Anything more goes through the records-request process |

A student can share more on a single note (`share: [parent, teacher]`) or mark it
`private`. Grades and milestones can't be hidden from parents.

**Viewer host (recommended): Formation Pathways.** It already has staff and family logins,
consent records, row-level security, and separate staging and production databases. Its
database becomes the store for **views**, not truth: "one database" now means one place to
*see*, while each person's device stays the source. Alternatives considered: a static
Quartz site per audience (has no per-person login) and device-to-device sync (parents
don't have school devices).

## The editor: Obsidian, for now

Obsidian on the device: offline, plain Markdown, graph, backlinks and Bases with no
community plugins, mature on Linux (installed here, 1.14.4). It's closed source, but
because the files are plain Markdown, it's easy to replace. Others considered:

- **Logseq**: open source, but built around an outliner; check whether its newer
  database version still keeps plain files before relying on it.
- **Joplin, Anytype**: store notes in their own database, not a plain folder.
- **SilverBullet**: open source, plain Markdown, browser-based. Worth a look for
  Chromebook or phone access later.

None of them offers per-audience sharing, so the views are ours to build either way. For
students, `.obsidian/` is managed by pacos and community plugins are off.

## Mastery graph

What a student has mastered, as a picture: **joints → core ideas → objectives**, each node
colored by its latest level word (Not yet, Beginning, Developing, Proficient, Extending).
It is built **from the structured files we already have** (`ideas.toml`, `plan.toml`,
mastery levels), with no AI, so it shows the teacher's judgment and nothing guessed.

- On the device: `omalocker mastery` writes one offline HTML page and Markdown notes, so
  Obsidian's graph shows it too (color groups by level tag).
- In views: the same graph, cut to the audience (parent: core ideas; teacher: their
  class's objectives).
- **Graphify** (open source, `pip install graphifyy`) builds a graph of a whole folder, but
  it sends Markdown to Claude to find concepts. So: use it on **curriculum files only**
  (syllabi, long-range plans) to find connections between courses and suggest joints.
  Never run it on a real Locker or on rosters until the AI policy allows that.

## Connections to test

| Project | Flow | Contract | Test |
|---|---|---|---|
| **OmaMastery** (`~/Classes`) | Teacher device | Class folders live in the teacher's Locker; `ideas.toml`/`plan.toml` → `Classes/`, `Ideas/` notes; levels → mastery graph | Sample classes import; graph renders; `roster.toml`/`mastery.csv` never read by agents |
| **Teacher → student levels** | via viewer host | Teacher pushes a class's levels; the student's Locker pulls its own into `Mastery/<class>.md` | Fictional class: a level change reaches the student and the parent view |
| **Formation Pathways** | Device → host (views); host → Locker (pathway copy) | View files per audience; FP RLS checks each person's role | **Staging only**: fictional student, parent, teacher logins each see the right view |
| **Grades → system of record** | unchanged | Existing path, not touched | Confirm OmaLocker sends no grades anywhere new |
| **OmaClass** (Veyon) | Classes → Locker | `room` → class note property | Room shows on class note |
| **pacos** | install | `omalocker` package; `~/Locker` from `template/`; managed `.obsidian/` | VM: teacher and student (`beno29`) get a Locker; student can't turn on plugins |
| **PacTerminus** | Terminus → Locker | completion marker → `Pathway/Milestones.md` | VM: finish quest → milestone, visible in parent view |
| **Omawrite + Omacanvas turn-in** | both ways | Omawrite saves to `Work/<class>/`; turn-in submits from there | Fictional account submits a Locker file |
| **Canvas** | Canvas → Locker | OmaMastery setup's token: assignments → `Work/<class>/` stubs | Sandbox course |
| **Backup** | device → school | Encrypted backup of the whole Locker (see decisions) | Wipe the VM, restore, links intact |

`make test-connections` builds a fictional school in a temp `HOME` and runs every flow,
then `omalocker doctor` checks frontmatter, links, that each view holds only what its
audience may see, and that no real names leak.

## Phases

**0. Format.** `docs/format.md` (now with `share`), `template/`, ~20 fictional notes in
Obsidian.
**1. Teacher Locker + mastery graph on seno's machine.** `init`, `import classes`,
`mastery`, `doctor`, `make test-connections`; `~/Classes` moves into `~/Locker/Classes`
with a symlink.
**2. Views on FP staging.** Build views on the device, push to staging, fictional parent,
teacher and advisor logins.
**3. Student Locker in the pacos VM.** Package, managed Obsidian, Terminus milestone,
Omawrite, encrypted backup and restore.
**4. Pilot.** One class, after leadership signs off on the decisions below.

## Decisions still open

1. **Backup is now required**, because the device is the truth. Recommended: encrypted
   (restic) to school storage, with the key held by school IT in escrow.
2. **FERPA.** Teacher notes about students are education records, and parents have a legal
   right to inspect education records, so "high level by default" may not be enough on
   request. Students' own notes are a different category. Leadership and counsel need to
   confirm both.
3. **Parent access after 18** (FERPA rights move to the student), and for divorced or
   non-custodial parents: FP's guardian records need to say who counts as a parent.
4. **Viewer host** = Formation Pathways (recommended) vs. a separate app.
5. Obsidian's terms for school use (check the current terms; don't assume).

## Risks

- Device lost before its first backup = data lost. No pilot without tested backup.
- `.obsidian/` can load code: managed by pacos for students, not writable.
- Views get out of date when a device is offline. Show "as of <time>" on every view.
- Single point of failure (only seno): keep the format readable with a text editor.
