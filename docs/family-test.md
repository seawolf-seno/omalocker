# Family test: end to end with one real student

The first test with a real person: Mr. Eno's child as the student, Mr. Eno as the parent (and
as the teacher, if the child is in one of his classes). Mr. Eno gave permission on
2026-11-12, as the parent and as seno.

**Nothing goes to the cloud.** Nothing goes to Vercel, Turso or Resend: those have no data
agreements, and IT (Mr. Mulligan) asked us not to sign new ones. The viewer runs on Samuel's
laptop with a local SQLite file, behind Caddy with its own certificate authority. Sign-in
links are printed and handed over in person, not emailed.

| Laptop | Who | Runs |
|---|---|---|
| Samuel's | admin | `omalocker-viewer` (production, local data) + Caddy |
| the child's | student | `~/Locker` in Obsidian, `omalocker push`, `pull-levels` |
| Mr. Eno's | teacher and parent | `omalocker send-levels`; a browser for the parent view |

All three have to be on the same network (the same Wi-Fi). If the school Wi-Fi blocks
laptops from reaching each other, use a phone hotspot.

Rules for this test:
- The child's notes stay on the child's laptop. Only views leave it, as always.
- Agents never open the child's Locker, the views, or the viewer's data folder.
- The viewer's data stays outside this repo: `~/.local/share/omalocker-viewer-family`.

## 1. Samuel's laptop: the viewer

```sh
sudo pacman -S caddy
IP=$(ip -4 -br addr show wlan0 | awk '{print $3}' | cut -d/ -f1)
export OMALOCKER_VIEWER_DATA=~/.local/share/omalocker-viewer-family
viewer/omalocker-viewer init --env production --base-url "https://$IP:8443"
viewer/omalocker-viewer person add --name "Mr. Eno" --email <eno school email> --admin
viewer/omalocker-viewer person add --name "<child>" --email <child school email> --student \
    --grad-year <year> --blackbaud-id <id>        # the id from Mr. Eno's roster, for levels
viewer/omalocker-viewer grant parent --person <eno email> --student <child email> --primary-custody
viewer/omalocker-viewer grant teacher --person <eno email> --student <child email> --scope "<class name>"
viewer/omalocker-viewer push-token <child email>   # shown once: goes to the child's laptop
viewer/omalocker-viewer push-token <eno email>     # shown once: goes to Mr. Eno's laptop
viewer/omalocker-viewer serve                       # 127.0.0.1:8380; leave it running
```

In a second terminal, Caddy (it makes its own CA and a certificate for the IP):

```sh
caddy run --adapter caddyfile --config - <<EOF
{
    auto_https disable_redirects   # no port 80 (needs root)
    skip_install_trust             # don't add the CA to this laptop's trust store
}
https://$IP:8443 {
    tls internal
    reverse_proxy 127.0.0.1:8380
}
EOF
```

The CA certificate that the other two laptops need is
`~/.local/share/caddy/pki/authorities/local/root.crt`. Copy it to them on a USB stick; it
is public, so that's fine.

The teacher grant (and `--blackbaud-id`) only matters if the child is in one of
Mr. Eno's classes. If not, skip both; the levels steps below won't apply.

## 2. The child's laptop: the Locker

Omarchy (or any Linux or macOS with Python 3.11+). Have the child's push token and
`~/viewer-ca.crt` (from Samuel's laptop) ready to paste; then on the child's laptop:

```sh
curl -fsSL https://raw.githubusercontent.com/seawolf-seno/omalocker/main/install.sh \
    | bash -s -- --viewer https://<Samuel's IP>:8443
```

On Omarchy it asks for the child's password once (pacman), installs Obsidian and restic,
builds and installs the `omalocker` package (the one school laptops get), and puts "Locker"
in the app launcher (Super + Space). Elsewhere it installs into `~/.local` without root.
Then it creates `~/Locker` (never overwrites) and adds it as an Obsidian vault, asks for the
token (hidden) and the certificate (pasted), writes `~/.config/omalocker/viewer.toml` with
`ca_file`, turns on the hourly sync, and pushes once.

Then the child opens `~/Locker` in Obsidian and writes a few real notes: a class note, a
piece of work, a milestone, and one note with `share: [private]`.

```sh
omalocker doctor
omalocker push
```

## 3. Mr. Eno's laptop: levels (only if the child is in his class)

The same three files in `~/.config/omalocker/` (CA, his own token, `viewer.toml`), then:

```sh
omalocker send-levels
```

Back on the child's laptop: `omalocker pull-levels`, then `omalocker push`. The levels are
now in `Mastery/<class>.md` and in the parent view.

## 4. Mr. Eno signs in as the parent

On Samuel's laptop: `viewer/omalocker-viewer sign-in-link <eno email>` (valid 15 minutes,
once). He opens it on his phone or laptop. The browser warns about the certificate because
Caddy's CA is local; accept it for this test only.

## What to check

- [ ] The parent view opens on the overview, with "as of" and the right child.
- [ ] The child's private note is in no view.
- [ ] The milestone and the levels show, and private doesn't hide them.
- [ ] As a teacher, Mr. Eno sees only notes shared with his class.
- [ ] After the child edits a note and pushes again, the parent view changes.
- [ ] After the child marks a note private and pushes, it's gone from every view.
- [ ] `viewer/omalocker-viewer audit --student <child email>` lists every open.
- [ ] `omalocker push` refuses a viewer URL that isn't https.
- [ ] Without `ca_file`, push refuses the viewer (unknown certificate).

Write down what broke or confused anyone; that goes on Fizzy card 50.

## After the test

Mr. Eno chooses: keep the viewer data for another round, or delete it with
`viewer/omalocker-viewer graduate <child email> --yes` and then
`rm -r ~/.local/share/omalocker-viewer-family ~/.local/share/caddy`. The child keeps their
Locker either way. Remove the three files in `~/.config/omalocker/` on both laptops so the
hourly push stops.
