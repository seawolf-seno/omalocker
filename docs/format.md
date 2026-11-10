# Locker format (v0, draft)

A Locker is a folder (`~/Locker`) of Markdown notes with YAML frontmatter (Obsidian
"properties"). Every note has a `type`. Links are `[[wikilinks]]`, also inside properties.

```
~/Locker/
  Home.md          start here: this week, links to everything
  Me.md            who I am: role, grad year, pathway
  AGENTS.md        rules for AI agents
  Classes/         one note per class (teachers: OmaMastery's class folders live here too)
  People/          teachers, mentors, classmates; for teachers, students (private)
  Activities/      clubs, sports, service, arts, ministry, jobs
  Ideas/           core ideas and the joints that connect subjects
  Journal/         YYYY-MM-DD.md, one per day
  Work/<class>/    assignments, projects, writing
  Pathway/         goals, milestones, Formation Pathway copy
  Mastery/         levels copied from teachers (students); graph output
  Inbox/           quick capture, sorted later
```

## Types and properties

| type | properties |
|---|---|
| `class` | `course`, `teacher` (link), `block`, `day` (A/B), `room`, `term`, `ideas` (links), `source` |
| `person` | `role` (student/teacher/staff/mentor/family), `grad_year`, `classes`, `activities`, `private: true` for teacher notes about students |
| `activity` | `kind`, `leader` (link), `season`, `ideas` |
| `idea` | `joint` (link to the shared joint), `classes` |
| `journal` | `date`, `classes`, `people`, `activities` |
| `work` | `class`, `due`, `status` (idea/draft/turned-in/returned), `ideas`, `canvas_assignment` |
| `milestone` | `date`, `source` (e.g. `pacterminus`), `evidence` |
| `pathway` | `updated`, `source` (`formation-pathways`) |

Any note may add `share`: `private` (owner only), or a list of extra audiences
(`parent`, `teacher`, `advisor`, `activity`), on top of the defaults in `docs/plan.md`.
Mastery copies from teachers go in `Mastery/<class>.md` (generated, read-only).

`source` marks notes an app created. Apps rewrite only their own block:

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
