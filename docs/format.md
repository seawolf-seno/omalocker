# Locker format (v0, draft)

A Locker is a folder (`~/Locker`) of Markdown notes with YAML frontmatter (Obsidian
"properties"). Every note has a `type`. Links are `[[wikilinks]]`, also inside properties.

```
~/Locker/
  Home.md          start here: this week, links to everything
  Me.md            who I am: role, grad year, pathway
  AGENTS.md        rules for AI agents (type: guide)
  Classes/         one note per class (teachers: OmaMastery's class folders live here too)
  People/          teachers, mentors, classmates; for teachers, students (private)
  Activities/      clubs, sports, service, arts, ministry, jobs
  Ideas/           core ideas (type: idea) and the joints that connect subjects (type: joint)
  Journal/         YYYY-MM-DD.md, one per day
  Work/<class>/    assignments, projects, writing
  Pathway/         goals (written in the Locker; nothing comes from FP)
  Pathway/Milestones/  one note per milestone, YYYY-MM-DD <name>.md
  Mastery/         levels copied from teachers (students), one note per class; graph output
  Inbox/           quick capture, sorted later
```

## Types and properties

| type | properties |
|---|---|
| `class` | `course`, `teacher` (link), `block`, `day` (A/B), `room`, `term`, `ideas` (links), `source`, `omamastery` (the class's folder id, set by import) |
| `person` | `role` (student/teacher/staff/mentor/family), `grad_year`, `classes`, `activities`; teacher notes about students get `share: [private]` |
| `activity` | `kind`, `leader` (link), `season`, `ideas` |
| `idea` | `joint` (link to its joint note), `classes` |
| `joint` | `classes` (links): a big idea shared across subjects; ideas link to it |
| `journal` | `date`, `classes`, `people`, `activities` |
| `work` | `class`, `due`, `status` (idea/draft/turned-in/returned), `ideas`, `canvas_assignment` |
| `milestone` | `date`, `source` (e.g. `pacterminus`), `evidence`. One note each in `Pathway/Milestones/` |
| `pathway` | `updated` |
| `mastery` | `class` (link), `source`, `scope` (`class` on a teacher's device: counts per level, no names), `as_of` (date of the newest level). Generated in `Mastery/<class>.md`, read-only |
| `objective` | `class`, `idea` (links), `week`, `level` (most common level word), `tags` (`level/<word>`, for Obsidian graph colors), `source`, `omamastery` (objective id). Generated in `Mastery/<class>/`, read-only |
| `home` | none. `Home.md` only |
| `inbox` | none. Quick capture in `Inbox/` |
| `guide` | none. `AGENTS.md` only |

Any note may add `share`, always a list: `[private]` (owner only), or extra audiences
(`parent`, `teacher`, `advisor`, `activity`) on top of the defaults in `docs/plan.md`.
`private` can't be combined with other audiences. `omalocker views` applies these rules; `private` doesn't hide
`milestone`, `mastery` or `objective` notes from parents.

`source` marks notes an app created. Apps rewrite only their own block, plus the
properties they own (for `omalocker import classes`: a class note's `course`, `block`,
`day`, `room`, `term`, `ideas`; an idea's `joint`; the import's own links in `classes`).
Other properties and everything outside the block stay as the person wrote them:

```
<!-- omalocker:omamastery -->
...generated...
<!-- /omalocker:omamastery -->
```

## Rules

- Words, not scores. No points, streaks or failure language (same as OmaMastery).
- Real student names only in the owner's own Locker; never in this repo, fixtures,
  Fizzy or an agent prompt until the AI policy allows it.
- `template/` and test fixtures are fictional.
