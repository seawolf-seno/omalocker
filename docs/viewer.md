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
- Not built yet: graduation (delete a student's views, records and logins), the teacher →
  student levels flow, attachments, an audit log of who opened what, rate limits.

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

## Staging and production

`init --env staging` takes only reserved test addresses (`example.org`, `*.example`,
`*.test`), so real people can't be added by mistake; every page says STAGING.
`--env production` refuses those addresses and needs an `https://` base URL. Keep them in
separate data folders on separate machines.

## Set up (staging)

```sh
export OMALOCKER_VIEWER_DATA=/var/lib/omalocker-viewer   # the default
omalocker-viewer init --env staging --base-url https://locker-staging.school.example
omalocker-viewer person add --name "Rowan Teague" --email rowan@student.example.org --student --grad-year 2029
omalocker-viewer person add --name "Parent One" --email parent1@example.org
omalocker-viewer grant parent --person parent1@example.org --student rowan@student.example.org --primary-custody
omalocker-viewer grant teacher --person okafor@example.org --student rowan@student.example.org --scope Biology
omalocker-viewer push-token rowan@student.example.org     # shown once
omalocker-viewer sign-in-link parent1@example.org         # valid 15 minutes, once
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
- Session cookie: `HttpOnly`, `SameSite=Strict`, `Secure` when the base URL is https; 12 hours.
- Pages: strict Content-Security-Policy (no scripts at all), `no-store`, `no-referrer`,
  no framing. Note text is escaped; only headings, lists, tables, quotes, code, bold,
  italics and links are rendered. Wiki links resolve only to notes in the same view;
  web links only for `http(s)`.
- Server logs leave out paths, since they can hold student and note names.
