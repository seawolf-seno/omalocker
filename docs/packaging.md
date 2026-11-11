# Packaging (for pacos)

`make package` builds two Arch packages into `build/` from this repo (`pkgbuild/PKGBUILD`,
the same way OmaMastery is built). The tests run first (`check()`).

| Package | For | Installs |
|---|---|---|
| `omalocker` | every school laptop | `/usr/bin/omalocker`; the Locker template in `/usr/share/omalocker/template`; systemd user units; docs in `/usr/share/doc/omalocker` |
| `omalocker-viewer` | whoever runs the viewer (seno) | `/usr/bin/omalocker-viewer`, the admin command line |

`omalocker` depends on `python` (3.11+) and `restic`; Obsidian is optional.

## What runs on a laptop

Three user units, turned on for every user by the package (`systemctl --global preset`,
from `/usr/lib/systemd/user-preset/80-omalocker.preset`). Each does nothing until its
settings exist, so installing the package alone changes nothing for anyone.

| Unit | When | Does |
|---|---|---|
| `omalocker-setup.service` | each login, only while `~/Locker` doesn't exist | `omalocker init`, with the role from `/etc/omalocker/omalocker.toml` |
| `omalocker-backup.timer` | hourly | `omalocker backup --if-due`: an encrypted backup every 2 days (`docs/backup.md`) |
| `omalocker-push.timer` | hourly | `omalocker push --if-set-up`: rebuilds and sends a student's views; does nothing on a teacher's laptop, without viewer settings, or after graduation |

## What pacos has to put on each laptop

Nothing secret is in the package. pacos (or IT) writes these per laptop:

| File | Who reads it | Contents |
|---|---|---|
| `/etc/omalocker/omalocker.toml` | `omalocker init` | `role = "student"` (or `teacher`, `staff`) |
| `/etc/omalocker/backup.toml` | backup | `repository`, `password_file` (`docs/backup.md`); waiting on IT's storage |
| backup key file | backup | the restic key; readable by that person only |
| `/etc/omalocker/viewer.toml` | push (students only) | `url = "https://omalocker-viewer.vercel.app"`, `token_file = "/etc/omalocker/viewer-key"` |
| `/etc/omalocker/viewer-key` | push | the student's push token from `omalocker-viewer push-token <email>`; owned by the student, mode 600 |

## Not in this package (pacos side)

- **Locking Obsidian for students** (plan: community plugins off, `.obsidian/` not
  writable). The Locker's `.obsidian/` folder is made by Obsidian on first open; pacos
  should create it with `community-plugins.json` = `[]` and make `.obsidian/plugins/`
  unwritable for the student.
- **Adding `omalocker` to pacos's package list** and the VM test (teacher and student
  accounts get a Locker; the student can't turn on plugins).
- **Writing the files above** at device setup, with the push token and backup key from IT.

## Release

Bump `VERSION` in `bin/omalocker` and `viewer/omalocker-viewer` and `pkgver` in
`pkgbuild/PKGBUILD` together (a test checks they match), then `make package`.

## Checklist: OmaLocker in pacos

Written from this repo; where a step depends on how pacos does things, it says what's
needed rather than which pacos file to change.

**1. Get the package**
- [ ] In `omalocker`, run `make package`: `build/omalocker-<ver>-1-any.pkg.tar.*` (and
      `omalocker-viewer-…`, for seno's laptop only).
- [ ] Add `omalocker` to pacos's package list, the same way OmaMastery is included. It needs
      `python` and `restic`; add `obsidian` if pacos doesn't already install it.

**2. Settings every laptop gets** (written at device setup)
- [ ] `/etc/omalocker/omalocker.toml`: `role = "student"` on student laptops (`teacher` or
      `staff` on others). Mode 644.
- [ ] Nothing else is needed for teachers until backups are ready.

**3. Student laptops only: the viewer**
- [ ] For each student, on seno's laptop: `omalocker-viewer push-token <student email>`.
- [ ] Write it to `/etc/omalocker/viewer-key`, owned by the student, mode 600.
- [ ] Write `/etc/omalocker/viewer.toml`:
      ```toml
      url = "https://omalocker-viewer.vercel.app"
      token_file = "/etc/omalocker/viewer-key"
      ```

**4. Backups** (waiting on IT: storage and keys)
- [ ] `/etc/omalocker/backup.toml` with `repository` and `password_file` (`docs/backup.md`).
- [ ] The key file, readable by that person only; IT keeps a copy.

**5. Obsidian for students**
- [ ] Create `~/Locker/.obsidian/community-plugins.json` containing `[]`.
- [ ] Make `~/Locker/.obsidian/plugins/` unwritable by the student (owned by root, mode
      755), so community plugins can't be turned on.
- [ ] Hold student Obsidian until Obsidian's written OK for under-18s (`docs/plan.md`, open
      decision 1). Teachers can use it now.

**6. Test in the pacos VM** (fictional students only; staging takes `@example.org`-style
addresses)
- [ ] Teacher account: log in; `~/Locker` appears with `role: teacher` in `Me.md`.
- [ ] Student account: log in; `~/Locker` appears with `role: student`.
- [ ] Student: `systemctl --user list-timers` shows `omalocker-backup.timer` and
      `omalocker-push.timer`.
- [ ] Student: `systemctl --user start omalocker-push.service`, then
      `omalocker-viewer audit --limit 3` on seno's laptop shows the push.
- [ ] Student: open the Locker in Obsidian; turning on community plugins fails.
- [ ] Teacher: `systemctl --user start omalocker-push.service` succeeds and pushes nothing.

**7. When it passes**
- [ ] Note it on Fizzy card 50 and tick the "Phase 2: pacos package" step.
