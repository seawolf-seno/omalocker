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

step "Viewer (staging): fictional people, push from the student's device, role checks"
viewer="$repo/viewer/omalocker-viewer"
export OMALOCKER_VIEWER_DATA="$HOME/viewer" OMALOCKER_VIEWER_QUIET=1
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
base="http://127.0.0.1:$port"
"$viewer" init --env staging --base-url "$base"
"$viewer" person add --name "Rowan Teague" --email rowan@student.example.org --student --grad-year 2029
"$viewer" person add --name "Parent One" --email parent1@example.org
"$viewer" person add --name "Parent Two" --email parent2@example.org
"$viewer" person add --name "Mr. Okafor" --email okafor@example.org
"$viewer" grant parent --person parent1@example.org --student rowan@student.example.org --primary-custody
"$viewer" grant parent --person parent2@example.org --student rowan@student.example.org
"$viewer" grant teacher --person okafor@example.org --student rowan@student.example.org --scope Biology
"$viewer" push-token rowan@student.example.org 2>/dev/null > "$HOME/push-key"
printf 'url = "%s"\ntoken_file = "%s/push-key"\n' "$base" "$HOME" > "$HOME/viewer.toml"
export OMALOCKER_VIEWER_CONFIG="$HOME/viewer.toml"
"$viewer" serve --port "$port" & viewer_pid=$!
trap 'kill $viewer_pid 2>/dev/null; chmod -R u+rwx "$HOME"; rm -rf "$HOME"' EXIT
for _ in $(seq 50); do curl -s -o /dev/null "$base/" && break; sleep 0.1; done
"$omalocker" --locker "$student" push
sign_in() {  # sign in as $1 with a fresh link; cookie jar in $HOME/$1.jar
  local token
  token=$("$viewer" sign-in-link "$1" | sed 's/.*t=//')
  curl -s -o /dev/null -c "$HOME/$1.jar" --data-urlencode "t=$token" "$base/signin"
}
code() { curl -s -o /dev/null -w '%{http_code}' -b "$HOME/$1.jar" "$base$2"; }
sign_in parent1@example.org; sign_in parent2@example.org; sign_in okafor@example.org
[ "$(code parent1@example.org /s/1/parent/)" = 200 ]
[ "$(code parent2@example.org /s/1/parent/)" = 404 ]   # no primary custody
[ "$(code okafor@example.org /s/1/teacher/Biology/)" = 200 ]
[ "$(code okafor@example.org /s/1/teacher/Geometry/)" = 404 ]
[ "$(code okafor@example.org /s/1/parent/)" = 404 ]
if curl -s -b "$HOME/parent1@example.org.jar" "$base/s/1/parent/?all=1" | grep -q "summer labs"; then
  echo "a private note reached the viewer" >&2; exit 1
fi
echo "role checks pass: custodial parent, non-custodial parent, teacher"
"$viewer" audit --person okafor@example.org | grep -q "teacher/Biology"
"$viewer" audit --person okafor@example.org --denied | grep -q "parent  DENIED"
echo "access log records opens and refusals"

step "Graduation: hand over the Locker, stop the device, delete from the viewer"
"$omalocker" --locker "$student" graduate --to "$HOME/usb"
unzip -tq "$HOME/usb/"*.zip
unzip -l "$HOME/usb/"*.zip | grep -q "Locker/Inbox/ask about summer labs.md"   # private notes are theirs too
if "$omalocker" --locker "$student" push 2>/dev/null; then
  echo "a graduated Locker still pushed" >&2; exit 1
fi
"$viewer" graduate rowan@student.example.org | grep -q "Nothing deleted"
[ "$(code parent1@example.org /s/1/parent/)" = 200 ]
"$viewer" graduate rowan@student.example.org --yes
[ "$(code parent1@example.org /s/1/parent/)" = 303 ]   # login gone with the student
[ "$(code okafor@example.org /s/1/teacher/Biology/)" = 404 ]
"$viewer" list | grep -q okafor@example.org             # staff stay
if "$viewer" audit --limit 1000 | grep -q -e rowan@ -e parent1@; then
  echo "graduated student or family still in the access log" >&2; exit 1
fi
if "$viewer" list | grep -q -e rowan@ -e parent1@; then
  echo "graduated student or family still in the viewer" >&2; exit 1
fi

printf '\nAll connections pass.\n'
