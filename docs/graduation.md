# Graduation

The student keeps their Locker, and the school deletes its copies: the viewer (views,
login, family records) and the backups on school storage (decision 6). Do the steps in
order. The Locker is handed over **before** anything is deleted.

## 1. On the student's device: `omalocker graduate --to <folder>`

```sh
omalocker graduate --to /run/media/$USER/USB
```

- Writes `Locker YYYY-MM-DD.zip`: the whole Locker, private notes included (they're the
  student's), minus Obsidian's window layout and trash. It reads the zip back before
  going on; if anything fails, nothing changes.
- Marks the device as graduated (`~/.local/state/omalocker/graduated.json`): from now on
  `omalocker push` refuses, `omalocker backup` makes no new backups (the hourly timer just
  says so), and `doctor` shows the graduation date instead of backup warnings.
- Deletes the local copies of the views. The Locker itself stays on the device until the
  device is wiped.
- Never writes over an existing zip; it refuses to put the zip inside the Locker.

Give the student the zip. They unzip it and open the `Locker` folder in Obsidian, or any
text editor. Check together that it opens before going on.

## 2. On the viewer: `omalocker-viewer graduate <student email> --yes`

Run it without `--yes` first: it lists what will be deleted and deletes nothing.

Deletes, in one transaction: the student's views and notes, every grant to see them, the
push token, sign-in links and sessions, the student's login, and the login of every family
member with no other student in the viewer. Teachers, advisors, activity leaders, admins,
and parents of a sibling still in school stay. Deleted data is overwritten in the database
file (`secure_delete`, then `VACUUM`).

## 3. School IT: delete the backups

The device can't delete its own backups: storage is append-only so that a lost or broken
device can't either (`docs/backup.md`). On the backup server, delete the student's
repository, for example with `rest-server --private-repos`:

```sh
rm -rf /srv/restic/<student login>
```

and remove the student's key from IT's key store if keys are per person (open decision 2).

## Then

Wipe the device (pacos reinstall) before it's reused.

Not automated yet: steps 2 and 3 are run by hand by the viewer admin and IT. A checklist per
graduating class (who's done which step) is a later addition.
