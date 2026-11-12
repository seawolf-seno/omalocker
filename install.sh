#!/usr/bin/env bash
# Install OmaLocker for one person, without root: ~/Locker plus the omalocker command.
#
#   curl -fsSL https://raw.githubusercontent.com/seawolf-seno/omalocker/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/seawolf-seno/omalocker/main/install.sh \
#       | bash -s -- --viewer https://<viewer address>
#
# --viewer URL   also connect to a viewer: asks for the push token (and, for a viewer with
#                its own certificate, the certificate) and syncs every hour where systemd runs.
# --role ROLE    student (default), teacher or staff.
# --ca FILE      the viewer's certificate file, instead of pasting it.
#
# Never overwrites notes: an existing ~/Locker is left as it is. School laptops (pacos) get
# the package instead (docs/packaging.md). Rerun to update.
set -euo pipefail

REPO="seawolf-seno/omalocker"
REF="${OMALOCKER_REF:-main}"
SHARE="$HOME/.local/share/omalocker"
BIN="$HOME/.local/bin"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}/omalocker"
role=student viewer="" ca=""

say() { printf '%s\n' "$*"; }
die() { printf 'omalocker install: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --viewer) viewer="${2:?--viewer needs an address}"; shift 2 ;;
        --role) role="${2:?--role needs student, teacher or staff}"; shift 2 ;;
        --ca) ca="${2:?--ca needs a file}"; shift 2 ;;
        -h|--help) sed -n '2,15p' "$0" 2>/dev/null || true; exit 0 ;;
        *) die "unknown option $1" ;;
    esac
done
case "$role" in student|teacher|staff) ;; *) die "role must be student, teacher or staff" ;; esac
case "$viewer" in ""|https://*) ;; *) die "the viewer address must start with https://" ;; esac

command -v python3 >/dev/null || die "needs python3 (3.11 or newer)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
    || die "needs python3 3.11 or newer (this one is $(python3 -V 2>&1))"

# 1. The command and the Locker template, in ~/.local/share/omalocker.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
if [ -n "${OMALOCKER_SRC:-}" ]; then          # tests: install from a local checkout
    src="$OMALOCKER_SRC"
else
    command -v curl >/dev/null || die "needs curl"
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$tmp"
    src=$(echo "$tmp"/omalocker-*)
fi
[ -f "$src/bin/omalocker" ] && [ -d "$src/template" ] || die "download is missing bin/omalocker or template/"
mkdir -p "$SHARE/bin" "$BIN"
rm -rf "$SHARE/template"
cp -R "$src/template" "$SHARE/template"
install -m 755 "$src/bin/omalocker" "$SHARE/bin/omalocker"
ln -sf "$SHARE/bin/omalocker" "$BIN/omalocker"
om="$BIN/omalocker"
say "Installed $("$om" --version 2>/dev/null || echo omalocker) in $SHARE"

# 2. ~/Locker (never overwrites).
"$om" init --role "$role"

# 3. The viewer: the push token, and the certificate when the viewer has its own.
if [ -n "$viewer" ]; then
    [ -r /dev/tty ] || die "--viewer asks for the push token; run it in a terminal"
    mkdir -p "$CONF"
    chmod 700 "$CONF"
    printf 'Push token for this Locker (from the viewer admin; input hidden): ' >/dev/tty
    IFS= read -rs token </dev/tty
    printf '\n' >/dev/tty
    [ -n "$token" ] || die "no token given"
    (umask 077; printf '%s\n' "$token" > "$CONF/viewer-key")
    ca_line=""
    if [ -n "$ca" ]; then
        [ -f "$ca" ] || die "no certificate file at $ca"
        cp "$ca" "$CONF/viewer-ca.crt"
    elif ! python3 -c 'import ssl, sys, urllib.parse as u
p = u.urlsplit(sys.argv[1])
import socket
with socket.create_connection((p.hostname, p.port or 443), timeout=10) as s:
    ssl.create_default_context().wrap_socket(s, server_hostname=p.hostname).close()' "$viewer" 2>/dev/null; then
        say "This viewer uses its own certificate. Paste it (from -----BEGIN to -----END CERTIFICATE-----):" >/dev/tty
        : > "$CONF/viewer-ca.crt"
        while IFS= read -r line </dev/tty; do
            printf '%s\n' "$line" >> "$CONF/viewer-ca.crt"
            case "$line" in *"END CERTIFICATE"*) break ;; esac
        done
    fi
    if [ -f "$CONF/viewer-ca.crt" ]; then
        grep -q "BEGIN CERTIFICATE" "$CONF/viewer-ca.crt" || die "that isn't a certificate"
        ca_line="ca_file = \"$CONF/viewer-ca.crt\""
    fi
    cat > "$CONF/viewer.toml" <<EOF
url = "$viewer"
token_file = "$CONF/viewer-key"
$ca_line
EOF
    say "Viewer: $viewer"

    # Hourly sync, as on school laptops (systemd user timer), pointed at ~/.local/bin.
    if [ -z "${OMALOCKER_NO_TIMER:-}" ] && command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
        units="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
        mkdir -p "$units"
        for u in omalocker-push.service omalocker-push.timer; do
            sed "s#/usr/bin/omalocker#$om#g" "$src/systemd/$u" > "$units/$u"
        done
        systemctl --user daemon-reload
        systemctl --user enable --now omalocker-push.timer >/dev/null
        say "Syncing every hour (systemctl --user status omalocker-push.timer)."
    else
        say "No systemd here: run 'omalocker push' to send your views."
    fi
    if [ "$role" = student ]; then
        "$om" push || say "The first push didn't go through; check the address and token, then run: omalocker push"
    fi
fi

case ":$PATH:" in *":$BIN:"*) ;; *) say "Add $BIN to your PATH to type 'omalocker'." ;; esac
command -v obsidian >/dev/null || say "Next: install Obsidian (https://obsidian.md) and open ~/Locker as a vault."
say "Done. Check your Locker any time with: omalocker doctor"
