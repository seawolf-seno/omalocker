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
| Parent / guardian | Opens at the high level: course grades, milestones, mastery graph at the core-idea level, pathway. Can expand to everything else, including teacher notes about their child, except notes the student marked `private`. Only the parent with primary custody; access lasts until graduation, including after the student turns 18. |
| Teacher | Their own classes: the student's work and notes tagged with that class, objective-level mastery for that class |
| Advisor / counselor | All classes at the core-idea level, activities, pathway |
| Activity leader | Notes tagged with their activity |
| Admin | Same as parent, plus attendance-type records if added later. Anything more goes through the records-request process |

A student can share more on a single note (`share: [parent, teacher]`) or mark it
`private` (hidden from parents and everyone else). Only the student's own notes can be
marked private: grades, milestones and teacher notes about the student can't be hidden
from parents.

**Built: `omalocker views`** (2026-11-10) writes each view into
`~/.local/state/omalocker/views/` (outside the Locker), one folder per audience
(`parent/`, `advisor/`, `teacher/<class>/`, `activity/<activity>/`), each with a
`view.json` (`as_of`, notes, and for parents which notes are on the first page). It
rebuilds every view from scratch, so a note made private is gone on the next run; nothing
is sent until the student's device runs `omalocker push` (to the viewer, `docs/viewer.md`). How the rules above became filters:

- "Tagged with a class/activity" = the note's properties link to it. Teachers and activity
  leaders get that, the class/activity note itself, and `Me.md`.
- `share: [teacher]` reaches the teachers of the classes the note links, or every teacher
  if it links none. Same for `activity`.
- `People/` notes go only to parents, unless the student shares them.
- Never in any view: `private` notes, `AGENTS.md`, and notes about classmates
  (`role: student`), since they hold another student's information (seno, 2026-11-10:
  classmates stay out, parents included).
- `private` doesn't hide milestones or mastery; `doctor` says so on such a note.
- `doctor` fails if a built view holds a note its audience can't see now, and notes when
  views are older than the notes.
- Not yet: attachments (non-Markdown files), course grades, objective-level mastery on a
  student device (only teachers' devices have objective notes today).

**Viewer (decided): OmaLocker's own viewer app, fully separate from Formation Pathways**
(seno, 2026-11-10). No connection to FP at all: OmaLocker doesn't use FP's logins, its
family records, or its database, and FP sends nothing into a Locker. The viewer needs its
own:

- **Logins** for students, staff and parents.
- **Family records**: who is each student's parent, with a primary-custody field. Only the
  primary-custody parent gets a parent view.
- **Role checks**: every request checks the viewer's role against the student before
  showing a view.
- **Staging and production**, kept apart. Staging holds fictional people only.

It stores **views only**, never truth: each person's device stays the source. Alternatives
considered: a static Quartz site per audience (has no per-person login) and
device-to-device sync (parents don't have school devices).

## The editor: Obsidian, for now

Obsidian on the device: offline, plain Markdown, graph, backlinks and Bases with no
community plugins, mature on Linux (installed here, 1.14.4). It's closed source, but
because the files are plain Markdown, it's easy to replace. Its terms require users to be
adults, so students need Obsidian's written permission first (see open decisions). Others considered:

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
| **Teacher → student levels** | via the viewer | `omalocker send-levels` sends a class's levels by school id (no names); the student's Locker pulls its own into `Mastery/<class>.md` (`omalocker pull-levels`) | Built 2026-11-10: a fictional class's levels reach the student's note and the parent view; names never leave the teacher's laptop |
| **OmaLocker viewer** | Device → viewer (views only) | `omalocker push` sends the views; the viewer checks each person's role and, for parents, primary custody (`docs/viewer.md`) | Built and tested on a local staging viewer: fictional custodial and non-custodial parent, teacher, advisor, activity leader and admin each see the right view, or none. Still to do: a real staging host |
| **Formation Pathways** | none | No connection, either way | Confirm OmaLocker sends nothing to FP and reads nothing from it |
| **Grades → system of record** | unchanged | Existing path, not touched | Confirm OmaLocker sends no grades anywhere new |
| **OmaClass** (Veyon) | Classes → Locker | `room` (OmaMastery's `class.toml`, which OmaClass reads) → class note property: teacher's Locker by `import classes`, students' through `send-levels`/`pull-levels` | Built 2026-11-10: a room change reaches the teacher's and the student's class note and the parent overview |
| **pacos** | install | `omalocker` package; `~/Locker` from `template/`; managed `.obsidian/` | VM: teacher and student (`beno29`) get a Locker; student can't turn on plugins |
| **PacTerminus** | Terminus → Locker | completion marker (`~/.local/share/omaterminus/complete`, the finish time) → `Pathway/Milestones/<date> Finished PacTerminus.md` by `omalocker import pacterminus`, run by the hourly sync | Built 2026-11-10: marker → one milestone, on the parent's first page after the next push. Still: the VM run |
| **Omawrite + Omacanvas turn-in** | both ways | Omawrite saves to `Work/<class>/`; turn-in submits from there | Fictional account submits a Locker file |
| **Canvas** | Canvas → Locker | OmaMastery setup's token: assignments → `Work/<class>/` stubs | Sandbox course |
| **Backup** | device → school | `omalocker backup` (restic, encrypted) every 2 days via a systemd timer; school IT holds the key (`docs/backup.md`) | Built and tested: back up, wipe, restore, identical, `doctor` clean. Still to do: the same in the pacos VM against school storage |

`make test-connections` builds a fictional school in a temp `HOME` and runs every flow,
then `omalocker doctor` checks frontmatter, links, that each view holds only what its
audience may see, and that no real names leak.

## Phases

**0. Format.** `docs/format.md` (now with `share`), `template/`, ~20 fictional notes in
Obsidian.
**1. Teacher Locker + mastery graph on seno's machine.** `init`, `import classes`,
`mastery`, `doctor`, `make test-connections`; `~/Classes` moves into `~/Locker/Classes`
with a symlink.
**2. Viewer app on staging.** Build the viewer (logins, family records, role checks), build
views on the device, push to staging, fictional parent, teacher and advisor logins.
**3. Student Locker in the pacos VM.** Package (built 2026-11-10: `make package`,
`docs/packaging.md`), managed Obsidian, Terminus milestone, Omawrite, encrypted backup and
restore.
**4. Pilot.** One class, after leadership signs off on the decisions below.
**At graduation.** Built 2026-11-10 (`docs/graduation.md`): `omalocker graduate` zips the
Locker for the student and stops the device pushing and backing up; `omalocker-viewer
graduate` deletes their views, login and family records; IT deletes their backup repository.

## Decisions made (seno, 2026-11-10)

1. **Source of truth:** each person's device.
2. **Backup:** encrypted (restic) to school storage every 2 days. School IT holds the key,
   so a forgotten password doesn't lose a Locker. A lost device can lose up to 2 days of work.
3. **Parent access:** parents can see everything, but the view opens at the high level.
   Students can mark their own notes `private` from parents; teacher notes about the
   student, grades and milestones can't be hidden.
4. **After 18:** parents keep full access until graduation.
5. **Which parent:** the parent with primary custody. The viewer's family records have a
   primary-custody field.
6. **Graduation:** the student keeps their Locker, and their data is deleted from school
   servers (the viewer and backups).
7. **Viewer:** OmaLocker's own app, fully separate from Formation Pathways (no shared
   logins, records or data, and no pathway copy from FP).
8. **Classmates:** a student's notes about classmates go in no view, the parent view
   included.
9. **Viewer host (Mr. Eno, 2026-11-10):** Vercel. The viewer has to move off a long-running
   server and a local SQLite file (`docs/viewer.md`, "Moving to Vercel").
10. **Parent sign-in (Mr. Eno, 2026-11-10):** one-time sign-in links, emailed. To be tried
    with a real parent (Mr. Eno's wife) first.
11. **Phones first (Mr. Eno, 2026-11-10):** parents mostly use phones; the parent view has to
    be as easy as possible ("if she actually uses it, we're on to something").

Leadership and counsel should still confirm 3–5 against FERPA before the pilot (FERPA
rights normally move to the student at 18).

## Decisions still open

Asked Mr. Eno by email (2026-11-10): he answered where the viewer runs (Vercel) and parent
sign-in (emailed one-time links): decisions 9–10. Still open: 5 (custody records) and the
FERPA check.

Asked school IT by email (2026-11-10): a sending subdomain and DNS records for sign-in
emails, who signs data agreements (Resend, Vercel, Turso), backup storage, and decision 2
(backup key per person or per school). Waiting for an answer.

1. **Obsidian for students under 18.** Checked 2026-11-10 (terms, license and privacy
   policy all last updated 2025 or earlier):
   - **Cost:** free for schools. The license lists "educational institutions" under free
     use; the commercial license is optional.
   - **Age:** the terms say "You may use the Services only if you have reached the age of
     majority where you live", and "Services" includes the app. Nothing lets a parent or
     school accept for a student. Under the current terms, students under 18 can't use it.
   - **Privacy:** notes are "never sent to our servers"; no personal data or telemetry.
     The app only goes online for update checks, plugin and theme browsing, and embedded
     web pages; pacos turns these off for students.
   - **Asked (seno, 2026-11-10):** emailed Obsidian for written permission for students
     under 18 using the desktop app with no account, installed by the school. Waiting for
     the reply; keep it on file.
     Teachers and staff can use it now. If Obsidian says no, students get an open-source
     editor (SilverBullet or Logseq) instead; the Locker files don't change.
2. **Backup key: one per person or one for the school** (`docs/backup.md`). Recommended:
   one per person, made at device setup and copied to IT.
3. **Where the viewer runs** (a school server or a hosted service) and who keeps it running.
4. **How people sign in**: school accounts for students and staff; parents need another way
   (for example an emailed link).
5. **Where family and custody records come from** (for example the school's records in
   Blackbaud), and who updates them when custody changes.

## Risks

- Device lost before its first backup = data lost. No pilot without tested backup.
- `.obsidian/` can load code: managed by pacos for students, not writable.
- Views get out of date when a device is offline. Show "as of <time>" on every view.
- Single point of failure (only seno): keep the format readable with a text editor.
- The viewer is a new app holding student data, with its own logins: more to build and
  secure than reusing FP. Keep it small, and test the role checks in staging first.
- Family records in the viewer can drift from the school's records. A wrong custody record
  shows a student's Locker to the wrong parent.
