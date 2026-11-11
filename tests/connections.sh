#!/usr/bin/env bash
# Builds a fictional school in a temp HOME and runs every connection built so far.
# Phase 1: OmaMastery ~/Classes -> teacher Locker. Later phases add their flows here.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
omalocker="$repo/bin/omalocker"
export HOME=$(mktemp -d)
unset OMALOCKER_LOCKER OMALOCKER_NOW XDG_CONFIG_HOME XDG_STATE_HOME XDG_CACHE_HOME XDG_DATA_HOME
export OMALOCKER_BACKUP_CONFIG="$HOME/backup.toml"   # never /etc or the real ~/.config
trap 'chmod -R u+rwx "$HOME"; rm -rf "$HOME"' EXIT
step() { printf '\n== %s\n' "$*"; }

step "Teacher: fictional ~/Classes from OmaMastery"
cp -r "$repo/fixtures/classes" "$HOME/Classes"
chmod 000 "$HOME"/Classes/*/roster.toml "$HOME"/Classes/*/mastery.csv "$HOME"/Classes/*/notes.md 2>/dev/null || true

step "omalocker init --role teacher --move-classes"
"$omalocker" init --role teacher --move-classes
[ -L "$HOME/Classes" ] && [ -f "$HOME/Locker/Classes/biology/class.toml" ]

step "omalocker import classes (twice: second run changes nothing)"
"$omalocker" import classes
"$omalocker" import classes | grep -q "0 notes created, 0 updated"
test -f "$HOME/Locker/Classes/Biology.md"
test -f "$HOME/Locker/Ideas/Systems and feedback.md"
if grep -rq "Zz Fictional" "$HOME/Locker" --include='*.md' --exclude-dir=geometry; then
  echo "a roster name reached a Locker note" >&2; exit 1
fi

step "omalocker mastery (twice: second run changes nothing)"
chmod 644 "$HOME"/Locker/Classes/*/mastery.csv
"$omalocker" mastery
"$omalocker" mastery | grep -q "0 files created, 0 updated"
test -f "$HOME/Locker/Mastery/graph.html"
if grep -rq "Zz" "$HOME/Locker/Mastery" "$HOME/Locker/.obsidian"; then
  echo "a student name reached Mastery/" >&2; exit 1
fi

step "omalocker doctor"
"$omalocker" doctor

step "Backup: back up, wipe the Locker, restore, check"
restic_bin="${OMALOCKER_RESTIC:-$(command -v restic || true)}"
if [ -z "$restic_bin" ] || ! "$restic_bin" version >/dev/null 2>&1; then
  echo "skipped: restic isn't installed (pacman -S restic, or set OMALOCKER_RESTIC)"
else
  export OMALOCKER_RESTIC="$restic_bin"
  head -c 32 /dev/urandom | base64 > "$HOME/backup-key"
  printf 'repository = "%s/backup/{user}"\npassword_file = "%s/backup-key"\n' "$HOME" "$HOME" > "$OMALOCKER_BACKUP_CONFIG"
  chmod -R u+r "$HOME/Locker/Classes"
  "$omalocker" backup
  "$omalocker" backup --if-due | grep -q "next one is due"
  before=$(cd "$HOME/Locker" && find . -type f -print0 | sort -z | xargs -0 sha256sum)
  rm -rf "$HOME/Locker"
  "$omalocker" restore
  after=$(cd "$HOME/Locker" && find . -type f -print0 | sort -z | xargs -0 sha256sum)
  [ "$before" = "$after" ] || { echo "restored Locker differs" >&2; exit 1; }
  "$omalocker" doctor
fi

step "omalocker doctor on the Phase 0 sample Locker"
"$omalocker" --locker "$repo/fixtures/sample-locker" doctor

step "Student: views per audience from a copy of the sample Locker"
student="$HOME/student-locker"
cp -r "$repo/fixtures/sample-locker" "$student"
"$omalocker" --locker "$student" views
views="$HOME/.local/state/omalocker/views"
for v in parent advisor "teacher/Biology" "activity/Cross Country"; do
  test -f "$views/$v/view.json"
done
if grep -rq "summer lab" "$views"; then
  echo "a private note reached a view" >&2; exit 1
fi
if find "$views" -name "Jules Marchetti.md" | grep -q .; then
  echo "a classmate's note reached a view" >&2; exit 1
fi
"$omalocker" --locker "$student" doctor

printf '\nAll connections pass.\n'
