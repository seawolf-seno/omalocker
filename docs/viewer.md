# Viewer

OmaLocker's own app for parents, teachers, advisors and activity leaders: each person sees
only the views of a student's Locker they're allowed to see. Fully separate from Formation
Pathways (decision 7). It stores **views only**: each student's device builds them
(`omalocker views`) and sends them (`omalocker push`). The Locker itself never leaves the
device.

`viewer/omalocker-viewer`: one Python stdlib file (sqlite3 + http.server). Run it behind a
TLS proxy (for example Caddy); it listens on 127.0.0.1 by default.

## Status (2026-11-10): first version, staging only

Built and tested with fictional people (`make test`, `make test-connections`):
logins by one-time link, family records with primary custody, grants, role checks on every
page, push from the device, a safe Markdown renderer, "as of" on every view.

Still open (see `docs/plan.md`, decisions still open 3–5):
- **Where it runs** and who keeps it running. Until then: staging on a test machine.
- **How people sign in.** Today an admin prints a one-time link (`sign-in-link`) and hands it
  over. Next: email the link to parents; school accounts (SSO) for staff.
- **Where family and custody records come from.** Today they're entered with `grant`. Next:
  import from the school's records, and decide who updates custody changes.
- Graduation: `omalocker-viewer graduate <email>` (list) / `--yes` (delete); see
  `docs/graduation.md`.
- Not built yet: the teacher → student levels flow, attachments, rate limits.

## On Vercel with Turso (live on staging since 2026-11-10)

Staging: **https://omalocker-viewer.vercel.app** (Vercel project `omalocker-viewer` in
srsuchard's projects; Turso database `omalocker-viewer-staging` from Vercel's Marketplace,
which set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` on the project and in `.env.local`).
Fictional people only: Rowan Teague (student), parent@example.org (primary custody),
okafor@example.org (teacher, Biology). Run admin commands against it with
`(set -a; . ./.env.local; set +a; viewer/omalocker-viewer <command>)`.

Things Vercel needs that aren't obvious:
- `api/index.py` must declare `class handler(...)` literally; Vercel finds Python functions
  by reading the source, and `handler = something()` isn't found (the whole project then
  deploys as static files, source included).
- `vercel.json` uses `routes`, not `rewrites`: routes send every path to the function before
  static files are checked, so nothing in the repo is ever served as a file.
- `.vercelignore` excludes `.env*` and `.vercel`; a local `vercel build` otherwise bundles
  `.env.local` (the database token).
- `vercel build` writes `pyproject.toml` and `uv.lock`; they're in `.gitignore`.
- Runtime: Python 3.14.


- **Code:** `api/index.py` loads `viewer/omalocker-viewer` and hands Vercel its `handler`
  class (Vercel's Python runtime takes a `BaseHTTPRequestHandler`). `vercel.json` sends every
  path to it; `.vercelignore` uploads only `api/`, `viewer/` and `vercel.json`.
- **Database:** Turso (libSQL, SQLite's dialect), spoken over its HTTP API with the
  standard library, so the viewer still has no dependencies. Locally the same code uses a
  SQLite file. Pick with `--db libsql://...` (token in `TURSO_AUTH_TOKEN` or a file named by
  `OMALOCKER_VIEWER_DB_TOKEN_FILE`), or `--data DIR` for a local file. On Vercel:
  `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` (the names Turso's Vercel integration sets).
- **Settings** (`env`, `base_url`, `timezone`) are stored in the database by `init`, so the
  Vercel function and the admin CLI on your laptop read the same ones. Run `init` again after
  an upgrade: it adds missing tables and leaves settings alone.
- **Tests:** every viewer test runs twice, on a SQLite file and through a fake Turso server
  (`tests/fake_turso.py`), and `api/index.py` is loaded the way Vercel loads it.
- **Limits:** a Vercel function takes at most 4.5 MB per request, so a very large Locker's
  push will need splitting later.
- **Deleted data:** locally, graduation overwrites deleted rows (`secure_delete`, `VACUUM`).
  Turso keeps point-in-time backups, so deleted rows stay in its backups until they age out;
  check Turso's retention with IT before real data.
- **Still to do:** Resend for real sending (code ready, see "Signing in by email"); data processing
  agreements with Vercel, Turso and the mail service before any real student data.

### Set up staging

```sh
# 1. Turso database (through Vercel's Marketplace, or the Turso CLI); then locally:
export TURSO_AUTH_TOKEN=...            # never commit it
omalocker-viewer --db libsql://<db>.turso.io init --env staging --base-url https://<project>.vercel.app
# 2. Vercel: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN on the project, then deploy
vercel deploy
# 3. Fictional people, grants and a push token, as below, with --db instead of --data
```

## Signing in by email

The sign-in page asks for an email address and mails a one-time link (15 minutes). The page
says the same thing whatever was typed, so it never tells anyone who's on file. Students get
no link (they have their Locker). Limits: 3 links per address per hour, 200 for the whole
site. Every request is in the access log; an address that isn't on file isn't stored.

Mail goes out through [Resend](https://resend.com) (`RESEND_API_KEY`, and
`OMALOCKER_MAIL_FROM`, a sender on a domain verified in Resend). It is **never** really sent
on staging or to a test address: those go to the `outbox` table, read with
`omalocker-viewer outbox`. Production without Resend set up sends nothing and logs why.
`omalocker-viewer sign-in-link EMAIL --send` mails a link from the admin CLI.

To send for real: add Resend from Vercel's Marketplace (`resend/resend-email`), verify the
school's sending domain in Resend (DNS records from IT), set `OMALOCKER_MAIL_FROM`, and sign
a data processing agreement with Resend first: the emails carry parents' addresses.

## Who sees what

Every request checks the signed-in person against the student:

| Grant | Sees |
|---|---|
| `parent --primary-custody` | The family view (opens on Me, classes, mastery, milestones, pathway; "Show everything" for the rest) |
| `parent` without primary custody | Nothing. The record is kept, but only the primary-custody parent gets a view (decision 5) |
| `teacher --scope <class>` | That class's teacher view only. The scope is the class note's name in the Locker (`Classes/<name>.md`) |
| `advisor` | The advisor view |
| `activity --scope <activity>` | That activity's view only |
| admin (`person add --admin`) | The family view of every student (plan: admin = parent) |

Anything else is a 404, whether or not the view exists. Students don't use the viewer:
they have their Locker.

The viewer also re-checks every push and refuses one that holds a private note,
`AGENTS.md`, or a note about a classmate, even though the device already leaves them out.

## Access log

Every opened view and note, every refused attempt to open a student's view, sign-ins
(and failed ones), sign-outs, pushes (and refused ones), and every admin command (people,
grants, sign-in links, push tokens, graduation) are written to the `audit` table: time,
who (their email at the time), action, student, view, note path, result.

```sh
omalocker-viewer audit                         # newest 100
omalocker-viewer audit --student rowan@student.example.org
omalocker-viewer audit --person okafor@example.org --since 2026-11-01
omalocker-viewer audit --denied                # refused or failed only
omalocker-viewer audit --json
```

No IP addresses (behind the proxy they'd be the proxy's). Only the admin CLI reads it.

At graduation the student's entries are deleted with everything else (decision 6), and the
emails of deleted people are blanked in the rows that remain; one line records that a
graduation happened, with no name. **To confirm (seno, with counsel):** FERPA's record of
disclosures (34 CFR 99.32) is normally kept as long as the records; since the records
themselves are deleted, this deletes the log too. Also open: should families see who
opened their child's Locker?

## Staging and production

`init --env staging` takes only reserved test addresses (`example.org`, `*.example`,
`*.test`), so real people can't be added by mistake; every page says STAGING.
`--env production` refuses those addresses and needs an `https://` base URL. Keep them in
separate data folders on separate machines.

## Set up (staging)

```sh
export OMALOCKER_VIEWER_DATA=/var/lib/omalocker-viewer   # a local file; or --db for Turso
omalocker-viewer init --env staging --base-url https://locker-staging.school.example
omalocker-viewer person add --name "Rowan Teague" --email rowan@student.example.org --student --grad-year 2029
omalocker-viewer person add --name "Parent One" --email parent1@example.org
omalocker-viewer grant parent --person parent1@example.org --student rowan@student.example.org --primary-custody
omalocker-viewer grant teacher --person okafor@example.org --student rowan@student.example.org --scope Biology
omalocker-viewer push-token rowan@student.example.org     # shown once
omalocker-viewer sign-in-link parent1@example.org         # valid 15 minutes, once
omalocker-viewer sign-in-link parent1@example.org --hours 48   # staging only: a demo link to email (max 72)
omalocker-viewer serve                                    # 127.0.0.1:8380
omalocker-viewer list
```

On the student's device, `/etc/omalocker/viewer.toml` (or `~/.config/omalocker/viewer.toml`):

```toml
url = "https://locker-staging.school.example"
token_file = "/etc/omalocker/viewer-key"   # the push token, readable by the student only
```

Then `omalocker push` builds the views and sends them; every push replaces all of that
student's views. `omalocker push` only sends over `https://` (or to this machine).

## Security notes

- Tokens (sign-in links, sessions, push tokens) are random 256-bit values; only their
  SHA-256 is stored.
- Opening a sign-in link shows a button; the link is used only when it's pressed, so mail
  scanners that open links don't use it up.
- Session cookie: `HttpOnly`, `SameSite=Strict`, `Secure` when the base URL is https; 30 days,
  so a parent's phone stays signed in (signing out ends it). `timezone` in `config.toml`
  (default America/Los_Angeles) sets how times are shown.
- Pages: strict Content-Security-Policy (no scripts at all), `no-store`, `no-referrer`,
  no framing. Note text is escaped; only headings, lists, tables, quotes, code, bold,
  italics and links are rendered. Wiki links resolve only to notes in the same view;
  web links only for `http(s)`.
- Server logs leave out paths, since they can hold student and note names.
