"""Tests for bin/omalocker. Fictional data only. Run: make test"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("omalocker", str(REPO / "bin" / "omalocker"))
spec = importlib.util.spec_from_loader("omalocker", loader)
om = importlib.util.module_from_spec(spec)
loader.exec_module(om)


class Env(unittest.TestCase):
    """A temp HOME with a fictional ~/Classes."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp)
        self.saved_env = {k: os.environ.pop(k) for k in list(os.environ)
                          if k.startswith("XDG_") or k.startswith("OMALOCKER_")}
        # Never the real /etc or ~/.config backup settings.
        os.environ["OMALOCKER_BACKUP_CONFIG"] = str(self.tmp / "backup.toml")
        os.environ["OMALOCKER_DEVICE_CONFIG"] = str(self.tmp / "omalocker.toml")
        os.environ["OMALOCKER_VIEWER_CONFIG"] = str(self.tmp / "viewer.toml")
        self.locker = self.tmp / "Locker"
        self.classes = self.tmp / "Classes"
        shutil.copytree(REPO / "fixtures" / "classes", self.classes)

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp):
            for name in dirs + files:
                os.chmod(Path(root, name), 0o700, follow_symlinks=False) \
                    if not Path(root, name).is_symlink() else None
        shutil.rmtree(self.tmp)
        for k in [k for k in os.environ if k.startswith("XDG_") or k.startswith("OMALOCKER_")]:
            del os.environ[k]
        os.environ.update(self.saved_env)
        if self.old_home is not None:
            os.environ["HOME"] = self.old_home

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = om.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def note(self, rel):
        return (self.locker / rel).read_text()


class Packaging(unittest.TestCase):
    def test_versions_match(self):
        import re as _re
        pkgver = _re.search(r"^pkgver=(\S+)$", (REPO / "pkgbuild" / "PKGBUILD").read_text(), _re.M)
        viewer = _re.search(r'^VERSION = "([^"]+)"', (REPO / "viewer" / "omalocker-viewer").read_text(), _re.M)
        self.assertEqual(pkgver.group(1), om.VERSION)
        self.assertEqual(viewer.group(1), om.VERSION)

    def test_units_the_package_installs_exist(self):
        build = (REPO / "pkgbuild" / "PKGBUILD").read_text()
        preset = (REPO / "systemd" / "80-omalocker.preset").read_text()
        for unit in ("omalocker-setup.service", "omalocker-backup.timer", "omalocker-push.timer"):
            self.assertTrue((REPO / "systemd" / unit).exists(), unit)
            self.assertIn(f"enable {unit}", preset)
        for unit in ("omalocker-backup.service", "omalocker-push.service"):
            self.assertIn(unit, build)


class Frontmatter(unittest.TestCase):
    def test_round_trip(self):
        props = {"type": "class", "course": "Geometry: Proof & Space", "block": "1",
                 "room": None, "ideas": ["[[A]]", "[[B c]]"], "share": []}
        lines, body = om.split_note(om.dump_props(props) + "# Hi\n")
        self.assertEqual(om.parse_props(lines), props)
        self.assertEqual(body, "# Hi\n")

    def test_inline_lists_and_quotes(self):
        props = om.parse_props(['share: [private]', "a: ['x, y', \"z\"]", 'b: "[[L]]"'])
        self.assertEqual(props, {"share": ["private"], "a": ["x, y", "z"], "b": "[[L]]"})

    def test_rejects_unquoted_link_and_duplicates(self):
        with self.assertRaises(om.FormatError):
            om.parse_props(["teacher: [[Mr. Okafor]]"])
        with self.assertRaises(om.FormatError):
            om.parse_props(["type: idea", "type: joint"])

    def test_note_names(self):
        self.assertEqual(om.note_name("Geometry: Proof & Space"), "Geometry - Proof & Space")
        self.assertEqual(om.note_name("Advanced CS w/ AI Agents"), "Advanced CS w- AI Agents")


class Init(Env):
    def test_creates_and_never_overwrites(self):
        code, out, _ = self.run_cli("init", "--role", "teacher")
        self.assertEqual(code, 0)
        self.assertIn("role: teacher", self.note("Me.md"))
        self.assertTrue((self.locker / "Pathway" / "Milestones").is_dir())
        self.assertFalse(list(self.locker.rglob(".gitkeep")))
        (self.locker / "Me.md").write_text("mine")
        self.run_cli("init", "--role", "student")
        self.assertEqual(self.note("Me.md"), "mine")

    def test_role_comes_from_the_device_settings(self):
        Path(os.environ["OMALOCKER_DEVICE_CONFIG"]).write_text('role = "student"\n')
        self.assertEqual(self.run_cli("init")[0], 0)
        self.assertIn("role: student", self.note("Me.md"))

    def test_bad_device_role_stops_init(self):
        Path(os.environ["OMALOCKER_DEVICE_CONFIG"]).write_text('role = "wizard"\n')
        with self.assertRaises(SystemExit) as e:
            self.run_cli("init")
        self.assertIn("wizard", str(e.exception))
        self.assertFalse(self.locker.exists())

    def test_move_classes_leaves_a_link(self):
        self.run_cli("init")
        code, _, _ = self.run_cli("init", "--move-classes")
        self.assertEqual(code, 0)
        self.assertTrue(self.classes.is_symlink())
        self.assertTrue((self.classes / "biology" / "class.toml").exists())
        self.assertTrue((self.locker / "Classes" / "schedule.toml").exists())
        code, out, _ = self.run_cli("init", "--move-classes")
        self.assertEqual(code, 0)
        self.assertIn("already points", out)

    def test_move_classes_refuses_on_clash(self):
        self.run_cli("init")
        (self.locker / "Classes" / "biology").mkdir()
        code, _, err = self.run_cli("init", "--move-classes")
        self.assertEqual(code, 1)
        self.assertIn("biology", err)
        self.assertFalse(self.classes.is_symlink())
        self.assertTrue((self.classes / "geometry" / "plan.toml").exists())


class ImportClasses(Env):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--role", "teacher")

    def test_room_from_omaclass_shows_on_the_class_note(self):
        # class.toml's room is the Veyon room OmaClass uses; import copies it.
        self.run_cli("import", "classes")
        props, _ = om.read_note(self.locker / "Classes" / "Biology.md")
        self.assertEqual((props["room"], props["block"], props["day"]), ("S104", "2", "A"))
        toml = self.classes / "biology" / "class.toml"
        toml.write_text(toml.read_text().replace('room = "S104"', 'room = "S210"'))
        self.run_cli("import", "classes")
        props, _ = om.read_note(self.locker / "Classes" / "Biology.md")
        self.assertEqual(props["room"], "S210")
        # Geometry has no room yet: the property is there, empty.
        geometry = [om.read_note(n)[0] for n in (self.locker / "Classes").glob("*.md")
                    if om.read_note(n)[0].get("omamastery") == "geometry"]
        self.assertEqual(len(geometry), 1)
        self.assertIn(geometry[0].get("room"), (None, ""))

    def test_never_opens_private_files(self):
        private = [self.classes / "geometry" / n for n in ("roster.toml", "mastery.csv", "notes.md")]
        for p in private:
            p.chmod(0)
        code, _, err = self.run_cli("import", "classes")
        self.assertEqual(code, 0, err)
        text = "".join(p.read_text() for p in self.locker.rglob("*.md"))
        self.assertNotIn("Zz Fictional", text)

    def test_notes_and_links(self):
        self.run_cli("import", "classes")
        bio = self.note("Classes/Biology.md")
        self.assertIn("omamastery: biology", bio)
        self.assertIn("term: 2026-27", bio)
        self.assertLess(bio.index("<!-- /omalocker:omamastery -->"), bio.index("## My notes"))
        self.assertLess(bio.index("2026-10-05"), bio.index("2026-11-09"))  # by week
        self.assertIn("Sample class", bio)
        self.assertFalse((self.locker / "Classes" / "Old Class.md").exists())  # archive skipped
        joint = self.note("Ideas/Systems and feedback.md")
        self.assertIn("type: joint", joint)
        self.assertIn("[[Cellular respiration]]", joint)
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 0, out)

    def test_idempotent_and_keeps_own_words(self):
        self.run_cli("import", "classes")
        path = self.locker / "Classes" / "Biology.md"
        path.write_text(path.read_text().replace("## My notes\n", "## My notes\nMine.\n")
                        .replace("type: class\n", "type: class\nteacher: \"[[Me]]\"\n"))
        code, out, _ = self.run_cli("import", "classes")
        self.assertIn("0 notes created, 0 updated", out)
        (self.classes / "biology" / "plan.toml").write_text(
            '[[objective]]\nid = "x"\ntitle = "A new objective"\nidea = "Cellular respiration"\n')
        self.run_cli("import", "classes")
        text = path.read_text()
        self.assertIn("Mine.", text)
        self.assertIn('teacher: "[[Me]]"', text)
        self.assertIn("A new objective", text)
        self.assertNotIn("predator-prey", text)

    def test_renamed_note_and_class(self):
        self.run_cli("import", "classes")
        # Rename the way Obsidian does: the file and every link to it.
        (self.locker / "Classes" / "Biology.md").rename(self.locker / "Classes" / "Bio.md")
        for note in self.locker.rglob("*.md"):
            note.write_text(note.read_text().replace("[[Biology]]", "[[Bio]]"))
        toml = self.classes / "biology" / "class.toml"
        toml.write_text(toml.read_text().replace('"Biology"', '"Biology Honors"'))
        self.run_cli("import", "classes")
        self.assertFalse((self.locker / "Classes" / "Biology Honors.md").exists())
        self.assertIn("course: Biology Honors", self.note("Classes/Bio.md"))
        idea = self.note("Ideas/Cellular respiration.md")
        self.assertIn("[[Bio]]", idea)
        self.assertNotIn("[[Biology]]", idea)

    def test_keeps_classes_added_by_hand(self):
        path = self.locker / "Ideas" / "Argument from evidence.md"
        path.write_text('---\ntype: idea\nclasses:\n  - "[[English 10]]"\n---\n# Argument\n\nMy take.\n')
        self.run_cli("import", "classes")
        text = path.read_text()
        self.assertIn("[[English 10]]", text)
        self.assertIn("[[Geometry - Proof & Space]]", text)
        self.assertIn("My take.", text)

    def test_skips_note_of_another_type(self):
        (self.locker / "Ideas" / "Cellular respiration.md").write_text("---\ntype: work\n---\n")
        code, _, err = self.run_cli("import", "classes")
        self.assertEqual(code, 1)
        self.assertIn("work note", err)
        self.assertEqual(self.note("Ideas/Cellular respiration.md"), "---\ntype: work\n---\n")

    def test_needs_a_locker(self):
        shutil.rmtree(self.locker)
        code, _, err = self.run_cli("import", "classes")
        self.assertEqual(code, 1)
        self.assertIn("omalocker init", err)


class Mastery(Env):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--role", "teacher")
        self.run_cli("import", "classes")

    def test_counts_and_rollups(self):
        code, out, err = self.run_cli("mastery")
        self.assertEqual(code, 0, err)
        # Latest row wins (Zz Ava: Developing then Proficient); unknown words are ignored.
        feedback = self.note("Mastery/Biology/Model a predator-prey cycle and name its feedback.md")
        self.assertIn("level: Proficient", feedback)
        self.assertIn("level/proficient", feedback)
        self.assertIn("Levels: Proficient 3.", feedback)
        resp = self.note("Mastery/Biology/Explain how yeast releases energy with and without oxygen.md")
        self.assertIn("level: Beginning", resp)  # 1-1 tie goes to the lower level
        summary = self.note("Mastery/Biology.md")
        self.assertIn("as_of: 2026-11-12", summary)
        self.assertIn("scope: class", summary)
        # Joint: each student's lowest idea. Ava Beginning, Ben Proficient, Cy Proficient.
        html = self.note("Mastery/graph.html")
        data = json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])
        bio = data["classes"][0]
        self.assertEqual(bio["joints"][0]["dist"], [0, 1, 0, 2, 0])
        self.assertEqual(data["asOf"], "2026-11-12")
        code, out = self.run_cli("doctor")[:2]
        self.assertEqual(code, 0, out)

    def test_no_names_leave_the_csv(self):
        self.run_cli("mastery")
        for path in self.locker.rglob("*"):
            if path.is_file() and "Classes" not in path.parts:
                self.assertNotIn("Zz", path.read_text(), path)

    def test_idempotent_and_removes_dropped_objectives(self):
        self.run_cli("mastery")
        code, out, _ = self.run_cli("mastery")
        self.assertIn("0 files created, 0 updated", out)
        (self.classes / "biology" / "plan.toml").write_text(
            '[[objective]]\nid = "bio-feedback"\n'
            'title = "Model a predator-prey cycle and name its feedback"\n'
            'idea = "Feedback loops in ecosystems"\n')
        mine = self.locker / "Mastery" / "Biology" / "my own note.md"
        mine.write_text("---\ntype: inbox\n---\nMine.\n")
        code, out, _ = self.run_cli("mastery")
        self.assertIn("1 removed", out)
        self.assertFalse((self.locker / "Mastery" / "Biology" /
                          "Explain how yeast releases energy with and without oxygen.md").exists())
        self.assertTrue(mine.exists())

    def test_obsidian_colors_only_if_unset(self):
        graph = self.locker / ".obsidian" / "graph.json"
        graph.parent.mkdir()
        graph.write_text('{"colorGroups": [{"query": "path:Journal", "color": {"a": 1, "rgb": 1}}]}')
        self.run_cli("mastery")
        self.assertIn("path:Journal", graph.read_text())
        graph.write_text('{"showTags": false}')
        self.run_cli("mastery")
        config = json.loads(graph.read_text())
        self.assertFalse(config["showTags"])
        self.assertEqual(len(config["colorGroups"]), 5)

    def test_needs_class_notes(self):
        (self.locker / "Classes" / "Biology.md").unlink()
        code, _, err = self.run_cli("mastery")
        self.assertEqual(code, 1)
        self.assertIn("import classes", err)

    def test_class_without_levels(self):
        (self.classes / "biology" / "mastery.csv").unlink()
        self.run_cli("mastery")
        note = self.note("Mastery/Biology/Model a predator-prey cycle and name its feedback.md")
        self.assertIn("Not assessed yet.", note)
        self.assertIn("level/not-assessed", note)


def working_restic():
    """restic from OMALOCKER_RESTIC or PATH, if `restic version` runs (not a broken shim)."""
    import subprocess
    candidate = os.environ.get("OMALOCKER_RESTIC") or shutil.which("restic")
    try:
        ok = candidate and subprocess.run([candidate, "version"], capture_output=True).returncode == 0
    except OSError:
        ok = False
    return candidate if ok else None


RESTIC = working_restic()


class Backup(Env):
    def setUp(self):
        super().setUp()
        self.run_cli("init")
        shutil.rmtree(self.locker)
        shutil.copytree(REPO / "fixtures" / "sample-locker", self.locker)
        self.key = self.tmp / "key"
        self.key.write_text("fictional-test-key-0123456789\n")
        self.configure()

    def configure(self, **extra):
        lines = [f'repository = "{self.tmp}/repo/{{user}}"', f'password_file = "{self.key}"']
        lines += [f"{k} = {v}" for k, v in extra.items()]
        Path(os.environ["OMALOCKER_BACKUP_CONFIG"]).write_text("\n".join(lines) + "\n")

    def test_not_set_up(self):
        os.environ["OMALOCKER_BACKUP_CONFIG"] = str(self.tmp / "missing.toml")
        code, _, err = self.run_cli("backup")
        self.assertEqual(code, 1)
        self.assertIn("isn't set up", err)
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 0, out)
        self.assertNotIn("backup", out)

    def test_key_never_on_the_command_line(self):
        log = self.tmp / "argv.log"
        fake = self.tmp / "fake-restic"
        fake.write_text(f"#!/bin/sh\necho \"$@\" >> {log}\nenv | grep RESTIC_ >> {log}\n"
                        "echo 'Fatal: no' >&2; exit 1\n")
        fake.chmod(0o755)
        os.environ["OMALOCKER_RESTIC"] = str(fake)
        code, _, err = self.run_cli("backup")
        self.assertEqual(code, 1)
        logged = log.read_text()
        self.assertNotIn("fictional-test-key", logged)
        self.assertIn(f"RESTIC_PASSWORD_FILE={self.key}", logged)
        self.assertIn("can't open the backup repository", err)

    def test_unreadable_key(self):
        self.key.chmod(0)
        code, _, err = self.run_cli("backup")
        self.assertEqual(code, 1)
        self.assertIn("ask school IT", err)
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("never backed up", out)
        self.assertIn("ask school IT", out)


@unittest.skipUnless(RESTIC, "restic isn't installed")
class BackupWithRestic(Backup):
    def setUp(self):
        super().setUp()
        os.environ["OMALOCKER_RESTIC"] = RESTIC

    def at(self, days):
        os.environ["OMALOCKER_NOW"] = f"2026-11-{10 + days:02d}T12:00:00+00:00"

    def test_backup_wipe_restore(self):
        self.at(0)
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("never backed up", out)
        code, out, err = self.run_cli("backup")
        self.assertEqual(code, 0, err)
        self.assertIn("29 files", out)
        self.assertEqual(self.run_cli("doctor")[0], 0)

        code, out, _ = self.run_cli("backup", "--if-due")
        self.assertIn("next one is due", out)
        self.at(4)
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("4 days ago", out)

        code, _, err = self.run_cli("restore")
        self.assertEqual(code, 1)
        self.assertIn("nothing was restored over it", err)
        shutil.rmtree(self.locker)
        code, out, err = self.run_cli("restore")
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(p.relative_to(self.locker) for p in self.locker.rglob("*")),
                         sorted(p.relative_to(REPO / "fixtures" / "sample-locker")
                                for p in (REPO / "fixtures" / "sample-locker").rglob("*")))
        self.assertEqual(self.note("Journal/2026-11-10.md"),
                         (REPO / "fixtures" / "sample-locker" / "Journal" / "2026-11-10.md").read_text())
        code, out, _ = self.run_cli("--locker", str(self.locker), "doctor", "--json")
        self.assertEqual(json.loads(out)["issues"], [])

        other = self.tmp / "other"
        other.mkdir()
        (other / "x").write_text("x")
        code, _, err = self.run_cli("restore", "--to", str(other))
        self.assertEqual(code, 1)
        self.assertIn("isn't empty", err)
        self.assertFalse(list(self.tmp.glob(".omalocker-restore-*")))

    def test_if_due_and_keep_last(self):
        self.configure(keep_last=2)
        for day in (0, 2, 4):
            self.at(day)
            code, out, err = self.run_cli("backup", "--if-due")
            self.assertEqual(code, 0, err)
            self.assertIn("Backed up", out)
        self.at(5)
        self.assertIn("next one is due", self.run_cli("backup", "--if-due")[1])
        code, out, _ = self.run_cli("backup", "--status")
        self.assertIn("2 snapshots", out)

    def test_unreadable_file_still_backs_up_the_rest(self):
        secret = self.locker / "Inbox" / "locked.md"
        secret.write_text("---\ntype: inbox\n---\n")
        secret.chmod(0)
        code, out, err = self.run_cli("backup")
        self.assertEqual(code, 0, err)
        self.assertIn("couldn't be read", out)

    def test_wrong_key(self):
        self.run_cli("backup")
        self.key.write_text("a-different-key\n")
        code, _, err = self.run_cli("backup")
        self.assertEqual(code, 1)
        self.assertIn("can't open the backup repository", err)


class Doctor(Env):
    def setUp(self):
        super().setUp()
        self.run_cli("init")

    def write(self, rel, text):
        path = self.locker / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def doctor(self, *flags):
        code, out, _ = self.run_cli("doctor", "--json", *flags)
        return code, json.loads(out)["issues"]

    def test_sample_locker_is_clean(self):
        code, out, _ = self.run_cli("--locker", str(REPO / "fixtures" / "sample-locker"), "doctor")
        self.assertEqual(code, 0, out)

    def test_finds_problems(self):
        self.write("Inbox/a.md", "no frontmatter\n")
        self.write("Inbox/b.md", "---\ntype: thing\nshare: [private, parent]\n---\n[[Nowhere]]\n")
        self.write("Inbox/c.md", "---\ntype: inbox\n---\n<!-- omalocker:x -->\nopen\n")
        self.write("Journal/today.md", "---\ntype: journal\n---\n")
        self.write("Inbox/d.md", "---\ntype: inbox\nshare: private\n---\n`[[code]]` [[Me]] [[Me#Top|me]]\n")
        code, issues = self.doctor("--show-names")
        self.assertEqual(code, 1)
        by = {i["note"]: i for i in issues}
        self.assertIn("no frontmatter", by["Inbox/a.md"]["problems"][0])
        self.assertTrue(any("unknown type" in p for p in by["Inbox/b.md"]["problems"]))
        self.assertTrue(any("can't be combined" in p for p in by["Inbox/b.md"]["problems"]))
        self.assertEqual(by["Inbox/b.md"]["broken_links"], ["Nowhere"])
        self.assertTrue(any("never closed" in p for p in by["Inbox/c.md"]["problems"]))
        self.assertIn("Journal/today.md", by)
        self.assertEqual(by["Inbox/d.md"]["broken_links"], [])
        self.assertTrue(any("must be a list" in p for p in by["Inbox/d.md"]["problems"]))

    def test_hides_names_by_default(self):
        self.write("People/Zz Fictional.md", "---\ntype: person\n---\n[[Zz Friend]]\n")
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertNotIn("Zz", out)
        code, issues = self.doctor("--show-names")
        self.assertEqual(issues[0]["note"], "People/Zz Fictional.md")

    def test_never_opens_omamastery_files(self):
        self.run_cli("init", "--move-classes")
        for p in (self.locker / "Classes").rglob("*"):
            if p.is_file() and p.parent != self.locker / "Classes":
                p.chmod(0)
        (self.locker / "Classes" / "AGENTS.md").chmod(0)
        code, issues = self.doctor()
        self.assertEqual(code, 0, issues)


class Views(Env):
    """Views from the fictional Phase 0 sample (a sophomore's Locker)."""

    def setUp(self):
        super().setUp()
        shutil.copytree(REPO / "fixtures" / "sample-locker", self.locker)
        os.environ["OMALOCKER_NOW"] = "2026-11-10T20:00:00+00:00"
        self.out = self.tmp / ".local" / "state" / "omalocker" / "views"

    def build(self):
        code, out, err = self.run_cli("views")
        self.assertEqual(code, 0, err)
        return out

    def view(self, *parts):
        folder = self.out.joinpath(*parts)
        return {n["path"]: n for n in json.loads((folder / "view.json").read_text())["notes"]}

    def edit(self, rel, old, new):
        path = self.locker / rel
        path.write_text(path.read_text().replace(old, new, 1))

    def test_parent_sees_all_but_private_agents_and_classmates(self):
        self.build()
        parent = self.view("parent")
        for rel in ("Inbox/ask about summer labs.md", "AGENTS.md", "People/Jules Marchetti.md"):
            self.assertNotIn(rel, parent)
        for rel in ("Journal/2026-11-10.md", "People/Mr. Okafor.md", "Home.md",
                    "Work/Biology/Lab report - yeast respiration.md"):
            self.assertIn(rel, parent)
            self.assertFalse(parent[rel]["summary"])
        for rel in ("Me.md", "Classes/Biology.md", "Mastery/Biology.md",
                    "Pathway/Goals 2026-27.md",
                    "Pathway/Milestones/2026-11-08 League finals.md"):
            self.assertTrue(parent[rel]["summary"], rel)
        manifest = json.loads((self.out / "parent" / "view.json").read_text())
        self.assertEqual(manifest["as_of"], "2026-11-10T20:00:00+00:00")
        self.assertEqual((self.out / "parent" / "Me.md").read_text(), self.note("Me.md"))

    def test_teacher_sees_their_class(self):
        self.build()
        bio = self.view("teacher", "Biology")
        self.assertEqual(sorted(bio), [
            "Classes/Biology.md", "Ideas/Cellular respiration.md",
            "Ideas/Feedback loops in ecosystems.md", "Ideas/Systems and feedback.md",
            "Journal/2026-11-10.md", "Mastery/Biology.md", "Me.md",
            "Work/Biology/Lab report - yeast respiration.md"])
        # share: [teacher] on a note tagged English 10 reaches only that teacher.
        self.assertIn("Work/English 10/Personal essay draft.md", self.view("teacher", "English 10"))
        self.assertNotIn("Work/English 10/Personal essay draft.md", self.view("teacher", "Geometry"))

    def test_share_with_no_class_reaches_every_teacher(self):
        (self.locker / "Inbox" / "question.md").write_text(
            "---\ntype: inbox\nshare: [teacher]\n---\nA question.\n")
        self.build()
        for c in ("Biology", "English 10", "Geometry", "Theology 10"):
            self.assertIn("Inbox/question.md", self.view("teacher", c))
        self.assertNotIn("Inbox/question.md", self.view("advisor"))

    def test_advisor_and_activity(self):
        self.build()
        adv = self.view("advisor")
        self.assertIn("Pathway/Goals 2026-27.md", adv)
        self.assertIn("Activities/Robotics Club.md", adv)
        self.assertIn("Ideas/Systems and feedback.md", adv)
        for rel in adv:
            self.assertFalse(rel.startswith(("Journal/", "Work/", "People/", "Inbox/")), rel)
        xc = self.view("activity", "Cross Country")
        self.assertEqual(sorted(xc), [
            "Activities/Cross Country.md", "Journal/2026-11-09.md", "Me.md",
            "Pathway/Milestones/2026-11-08 League finals.md"])

    def test_private_note_leaves_every_view_on_rebuild(self):
        self.build()
        self.assertIn("Journal/2026-11-10.md", self.view("teacher", "Biology"))
        self.edit("Journal/2026-11-10.md", "type: journal", "type: journal\nshare: [private]")
        self.build()
        for p in self.out.rglob("*.md"):
            self.assertNotEqual(p.name, "2026-11-10.md", p)
        self.assertFalse(self.out.with_name("views.old").exists())

    def test_private_does_not_hide_milestones_from_parents(self):
        rel = "Pathway/Milestones/2026-11-08 League finals.md"
        self.edit(rel, "type: milestone", "type: milestone\nshare: [private]")
        self.build()
        self.assertIn(rel, self.view("parent"))
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("doesn't hide a milestone note from parents", out)

    def test_only_student_lockers(self):
        self.edit("Me.md", "role: student", "role: teacher")
        code, _, err = self.run_cli("views")
        self.assertEqual(code, 1)
        self.assertIn("only from a student's Locker", err)
        self.assertFalse(self.out.exists())

    def test_doctor_finds_leaks_and_stale_views(self):
        self.build()
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 0, out)
        self.edit("Me.md", "# Me", "# Me, edited")
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 0, out)
        self.assertIn("views are older than the notes", out)
        self.build()
        shutil.copy(self.locker / "Inbox" / "ask about summer labs.md",
                    self.out / "advisor" / "leak.md")
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("views hold 1 note their audience can't see", out)

    def test_graduate_exports_then_stops_push_and_backup(self):
        import zipfile
        self.build()
        (self.locker / ".obsidian").mkdir(exist_ok=True)
        (self.locker / ".obsidian" / "workspace.json").write_text("{}")
        (self.locker / ".obsidian" / "app.json").write_text("{}")
        usb = self.tmp / "usb"
        code, out, err = self.run_cli("graduate", "--to", str(usb))
        self.assertEqual(code, 0, err)
        zip_path = usb / f"Locker {om.now().astimezone().date().isoformat()}.zip"
        with zipfile.ZipFile(zip_path) as z:
            names = set(z.namelist())
            self.assertEqual(z.read("Locker/Me.md").decode(), self.note("Me.md"))
        self.assertIn("Locker/Inbox/ask about summer labs.md", names)  # private: still theirs
        self.assertIn("Locker/.obsidian/app.json", names)
        self.assertNotIn("Locker/.obsidian/workspace.json", names)
        self.assertEqual(len(names), sum(1 for p in self.locker.rglob("*") if p.is_file()) - 1)
        self.assertFalse(self.out.exists())          # local view copies gone
        self.assertTrue((self.locker / "Me.md").exists())  # the Locker stays

        code, _, err = self.run_cli("push")
        self.assertEqual(code, 1)
        self.assertIn("graduated", err)
        (self.tmp / "backup.toml").write_text('repository = "/x"\npassword_file = "/y"\n')
        code, out, _ = self.run_cli("backup", "--if-due")
        self.assertEqual(code, 0)
        self.assertIn("no more backups", out)
        self.assertEqual(self.run_cli("backup")[0], 1)
        code, out, _ = self.run_cli("doctor")
        self.assertIn("graduated on 2026-11-10", out)
        self.assertNotIn("never backed up", out)

        code, _, err = self.run_cli("graduate", "--to", str(usb))
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)

    def test_graduate_only_students_and_outside_the_locker(self):
        code, _, err = self.run_cli("graduate", "--to", str(self.locker / "out"))
        self.assertEqual(code, 1)
        self.assertIn("outside the Locker", err)
        self.edit("Me.md", "role: student", "role: teacher")
        code, _, err = self.run_cli("graduate", "--to", str(self.tmp / "usb"))
        self.assertEqual(code, 1)
        self.assertIn("for a student's Locker", err)
        self.assertFalse(om.graduated_path().exists())

    def test_push_for_the_timer_does_nothing_where_there_is_nothing_to_push(self):
        code, _, err = self.run_cli("push")
        self.assertEqual(code, 1)                      # by hand: say what's missing
        self.assertIn("isn't set up", err)
        self.assertEqual(self.run_cli("push", "--if-set-up")[0], 0)
        self.edit("Me.md", "role: student", "role: teacher")
        Path(os.environ["OMALOCKER_VIEWER_CONFIG"]).write_text(
            'url = "https://viewer.example"\ntoken_file = "/nonexistent"\n')
        code, out, _ = self.run_cli("push", "--if-set-up")
        self.assertEqual(code, 0)
        self.assertIn("not a student", out)
        self.edit("Me.md", "role: teacher", "role: student")
        self.run_cli("graduate", "--to", str(self.tmp / "usb"))
        self.assertEqual(self.run_cli("push", "--if-set-up")[0], 0)
        self.assertEqual(self.run_cli("push")[0], 1)

    def test_views_go_outside_the_locker(self):
        code, _, err = self.run_cli("views", "--out", str(self.locker / "views"))
        self.assertEqual(code, 1)
        self.assertIn("outside the Locker", err)


if __name__ == "__main__":
    unittest.main()
