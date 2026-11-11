# Turning in Locker work with Omacanvas

Omacanvas's **Turn in writing** (`turnin.py`) lets a student pick a Markdown file and
submits it to the open Canvas assignment. A Locker work note (`Work/<class>/<title>.md`) is
more than the writing, so turning one in as-is would send the teacher its properties
(`type: work`, `share: ...`), `[[link]]` brackets and `%% private comments %%`.

The Locker side is built here (2026-11-10). Omacanvas needs three small changes (not made:
that's the Omacanvas repo).

## What omalocker provides

| Command | Does |
|---|---|
| `omalocker submission <note>` | Prints only the writing: no properties, no `%% comments %%`, no `omalocker` app blocks, no embeds (`![[...]]`); `[[target\|words]]` become `words`, `[[target]]` becomes `target`. Exits 1 with "nothing to turn in" when there's no writing. |
| `omalocker turned-in <note> --assignment <url>` | Sets `status: turned-in` and `canvas_assignment: <url>` on the work note (the student's writing is untouched). Refuses notes outside `~/Locker`, notes that aren't `type: work`, and links that aren't `https://<canvas>/courses/<id>/assignments/<id>`. |

The next hourly sync carries the new status into the class's teacher view.

## Changes for Omacanvas (`turnin.py`)

1. **Start the file picker in the Locker.** In `pick_file`, prefer `~/Locker/Work` when it
   exists, then `~/Documents` as now:
   ```python
   work = os.path.expanduser("~/Locker/Work")
   start = work if os.path.isdir(work) else docs
   ```
2. **Submit the writing, not the file.** In `confirm`, when `omalocker` is installed and the
   file is in `~/Locker`, use its output as `text` (also for the word count in the dialog):
   ```python
   if shutil.which("omalocker") and path.startswith(os.path.expanduser("~/Locker/")):
       done = subprocess.run(["omalocker", "submission", path], capture_output=True, text=True)
       if done.returncode != 0:
           self.win.show_notice(done.stderr.strip() or "Couldn't read that note.")
           return
       text = done.stdout
   ```
3. **Record the turn-in.** In `on_submitted`, after a successful submit of a Locker note:
   ```python
   subprocess.run(["omalocker", "turned-in", path, "--assignment",
                   f"https://{canvas_host}/courses/{course}/assignments/{assignment}"])
   ```
   (`TurnIn` already has the course and assignment ids; keep `path` from `confirm`.)

Files outside the Locker keep working exactly as today.
