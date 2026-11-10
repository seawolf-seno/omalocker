#!/usr/bin/env bash
# Builds a fictional school in a temp HOME and runs every connection built so far.
# Phase 1: OmaMastery ~/Classes -> teacher Locker. Later phases add their flows here.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
omalocker="$repo/bin/omalocker"
export HOME=$(mktemp -d)
unset OMALOCKER_LOCKER
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

step "omalocker doctor on the Phase 0 sample Locker"
"$omalocker" --locker "$repo/fixtures/sample-locker" doctor

printf '\nAll connections pass.\n'
