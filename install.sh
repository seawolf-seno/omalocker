#!/usr/bin/env bash
# Install OmaLocker for one person: ~/Locker plus the omalocker command.
#
#   curl -fsSL https://raw.githubusercontent.com/seawolf-seno/omalocker/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/seawolf-seno/omalocker/main/install.sh \
#       | bash -s -- --viewer https://<viewer address>
#
# On Omarchy it builds and installs the omalocker package with pacman (asks for your password),
# installs Obsidian and restic, adds ~/Locker as an Obsidian vault, and puts "Locker" in the
# app launcher. Elsewhere (or with --no-package) it installs into ~/.local without root.
#
# --viewer URL   also connect to a viewer: asks for the push token (and, for a viewer with
#                its own certificate, the certificate) and syncs every hour where systemd runs.
# --role ROLE    student (default), teacher or staff.
# --ca FILE      the viewer's certificate file, instead of pasting it.
# --no-package   on Omarchy too: install into ~/.local, no pacman.
#
# Never overwrites notes: an existing ~/Locker is left as it is. School laptops (pacos) get
# the package from pacos instead (docs/packaging.md). Rerun to update.
set -euo pipefail

REPO="seawolf-seno/omalocker"
REF="${OMALOCKER_REF:-main}"
SHARE="$HOME/.local/share/omalocker"
BIN="$HOME/.local/bin"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}/omalocker"
role=student viewer="" ca="" package=auto

say() { printf '%s\n' "$*"; }
die() { printf 'omalocker install: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --viewer) viewer="${2:?--viewer needs an address}"; shift 2 ;;
        --role) role="${2:?--role needs student, teacher or staff}"; shift 2 ;;
        --ca) ca="${2:?--ca needs a file}"; shift 2 ;;
        --no-package) package=no; shift ;;
        -h|--help) sed -n '2,20p' "$0" 2>/dev/null || true; exit 0 ;;
        *) die "unknown option $1" ;;
    esac
done
case "$role" in student|teacher|staff) ;; *) die "role must be student, teacher or staff" ;; esac
case "$viewer" in ""|https://*) ;; *) die "the viewer address must start with https://" ;; esac
[ "$(id -u)" -ne 0 ] || die "run it as yourself, not as root (it asks for your password when needed)"

command -v python3 >/dev/null || die "needs python3 (3.11 or newer)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
    || die "needs python3 3.11 or newer (this one is $(python3 -V 2>&1))"

# 1. The source: the repo at $REF from GitHub.
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

omarchy=""
if [ -n "${OMALOCKER_OMARCHY:-}" ] || [ -d /usr/share/omarchy ] || [ -d "$HOME/.local/share/omarchy" ]; then
    omarchy=1
fi
if [ "$package" = auto ]; then
    if [ -n "$omarchy" ] && command -v pacman >/dev/null && command -v makepkg >/dev/null; then
        package=yes
    else
        package=no
    fi
fi

# 2. The omalocker command.
if [ "$package" = yes ]; then
    # Omarchy: the same package school laptops get (pkgbuild/), built here.
    PACMAN="${OMALOCKER_PACMAN:-sudo pacman}"     # tests stub this
    say "Installing Obsidian, restic and build tools (pacman may ask for your password)..."
    $PACMAN -S --needed --noconfirm base-devel python restic obsidian
    cp -R "$src" "$tmp/build-src"
    (cd "$tmp/build-src/pkgbuild" &&
        BUILDDIR="$tmp/makepkg" PKGDEST="$tmp/pkg" makepkg -f --nocheck --cleanbuild >/dev/null) \
        || die "building the package failed (makepkg in pkgbuild/)"
    pkg=$(ls "$tmp"/pkg/omalocker-[0-9]*.pkg.tar.* 2>/dev/null | head -1)
    [ -n "$pkg" ] || die "makepkg made no omalocker package"
    $PACMAN -U --noconfirm "$pkg"
    om="${OMALOCKER_BIN:-/usr/bin/omalocker}"     # tests point this at the repo
    say "Installed $("$om" --version 2>/dev/null || echo omalocker) (package $(basename "$pkg"))"
else
    # Anywhere else: the command and the Locker template in ~/.local/share/omalocker.
    mkdir -p "$SHARE/bin" "$BIN"
    rm -rf "$SHARE/template"
    cp -R "$src/template" "$SHARE/template"
    install -m 755 "$src/bin/omalocker" "$SHARE/bin/omalocker"
    ln -sf "$SHARE/bin/omalocker" "$BIN/omalocker"
    om="$BIN/omalocker"
    say "Installed $("$om" --version 2>/dev/null || echo omalocker) in $SHARE"
fi

# 3. ~/Locker (never overwrites).
"$om" init --role "$role"

# 4. The viewer: the push token, and the certificate when the viewer has its own.
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
    elif ! python3 -c 'import socket, ssl, sys, urllib.parse as u
p = u.urlsplit(sys.argv[1])
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
    printf 'url = "%s"\ntoken_file = "%s"\n%s\n' "$viewer" "$CONF/viewer-key" "$ca_line" > "$CONF/viewer.toml"
    say "Viewer: $viewer"

    # Hourly sync, as on school laptops (systemd user timer).
    if [ -z "${OMALOCKER_NO_TIMER:-}" ] && command -v systemctl >/dev/null \
            && systemctl --user show-environment >/dev/null 2>&1; then
        if [ "$package" = no ]; then          # the package brings its own units
            units="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
            mkdir -p "$units"
            for u in omalocker-push.service omalocker-push.timer; do
                sed "s#/usr/bin/omalocker#$om#g" "$src/systemd/$u" > "$units/$u"
            done
        fi
        systemctl --user daemon-reload
        systemctl --user enable --now omalocker-push.timer >/dev/null
        say "Syncing every hour (systemctl --user status omalocker-push.timer)."
    else
        say "No hourly sync here: run 'omalocker push' to send your views."
    fi
    if [ "$role" = student ]; then
        "$om" push || say "The first push didn't go through; check the address and token, then run: omalocker push"
    fi
fi

# 5. Obsidian: ~/Locker as a vault, and on Omarchy "Locker" in the app launcher.
locker=$(cd "$HOME/Locker" && pwd -P)
python3 - "$locker" "${XDG_CONFIG_HOME:-$HOME/.config}/obsidian/obsidian.json" <<'PY'
import json, os, secrets, sys, time
locker, path = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}
except ValueError:
    sys.exit(0)                      # leave a file we can't read alone
vaults = cfg.setdefault("vaults", {})
if not any(v.get("path") == locker for v in vaults.values()):
    vaults[secrets.token_hex(8)] = {"path": locker, "ts": int(time.time() * 1000)}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(cfg, f)
    os.replace(path + ".tmp", path)
    print("Obsidian: ~/Locker added as a vault")
PY
if [ -n "$omarchy" ]; then
    apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$apps"
    uri="obsidian://open?path=$(python3 -c 'import sys, urllib.parse as u; print(u.quote(sys.argv[1], safe=""))' "$locker")"
    printf '%s\n' "[Desktop Entry]" "Type=Application" "Name=Locker" \
        "Comment=My school life in Markdown (~/Locker), in Obsidian" \
        "Exec=obsidian \"$uri\"" "Icon=obsidian" "Categories=Education;Office;" "Terminal=false" \
        > "$apps/omalocker.desktop"
    say "App launcher: 'Locker' opens ~/Locker in Obsidian."
fi

if [ "$package" = no ]; then
    case ":$PATH:" in *":$BIN:"*) ;; *) say "Add $BIN to your PATH to type 'omalocker'." ;; esac
fi
command -v obsidian >/dev/null || say "Next: install Obsidian (https://obsidian.md) and open ~/Locker."
say "Done. Check your Locker any time with: omalocker doctor"
