# Backup

Every Locker is backed up, encrypted, to school storage every 2 days, and school IT holds
the key, so a forgotten password doesn't lose a Locker (decided 2026-11-10). No pilot until
a restore has been tested on a wiped device.

## How it works

- `omalocker backup` runs [restic](https://restic.net): the whole `~/Locker` (OmaMastery
  class folders included, for teachers), encrypted on the device before it leaves.
  Skipped: Obsidian's `workspace*.json` and `.trash`.
- A systemd user timer (`systemd/omalocker-backup.timer`) runs
  `omalocker backup --if-due` every hour. It backs up only when the last good backup is
  `every_days` old, so a laptop that was off catches up the next time it's on.
- `omalocker doctor` says when a Locker has never been backed up, or the last good backup is
  more than a day late, with the last error.
- `omalocker backup --status`: last good backup, last problem, snapshot count.
- `omalocker restore` never writes over notes. With `~/Locker` missing or empty (a wiped or
  new device) it restores there; otherwise use `--to <new folder>`, compare, then swap.
  `--snapshot <id>` picks an older one. Restores work from a different device: the newest
  snapshot of any host is used.

## What school IT sets up

`/etc/omalocker/backup.toml` (pacos installs it; a person can override it in
`~/.config/omalocker/backup.toml`):

```toml
repository = "rest:https://backup.school.example/{user}"   # {user}, {host} are filled in
password_file = "/etc/omalocker/backup-key"
every_days = 2
keep_last = 30   # snapshots the device keeps; 0 = never delete (append-only server)
```

- **Storage:** restic's `rest-server` with `--private-repos` (each login reaches only its own
  repository) and ideally `--append-only`, so a lost or broken device can't delete backups.
  With append-only, set `keep_last = 0` and prune on the server instead.
- **Key:** the password is read from `password_file` and passed to restic as a file, never
  on a command line. IT keeps a copy; that is what lets IT restore when a student forgets
  their password or loses the device.

## Open question

**One key per person, or one for the school?** A key per person (made when the device is
set up, copied to IT) means one leaked key opens one Locker. One school-wide key is simpler,
but a leaked key opens every repository its holder can reach (private repos limit that
reach). Recommended: one per person.

## Not yet

- Graduation: after `omalocker graduate`, the device makes no more backups; IT deletes the
  student's repository from school storage (`docs/graduation.md`).
- pacos: install `restic`, the settings file, the key, and enable the timer for every user.
