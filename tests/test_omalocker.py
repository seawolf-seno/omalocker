"""Tests for bin/omalocker. Fictional data only. Run: make test"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
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
        os.environ.pop("OMALOCKER_LOCKER", None)
        self.locker = self.tmp / "Locker"
        self.classes = self.tmp / "Classes"
        shutil.copytree(REPO / "fixtures" / "classes", self.classes)

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp):
            for name in dirs + files:
                os.chmod(Path(root, name), 0o700, follow_symlinks=False) \
                    if not Path(root, name).is_symlink() else None
        shutil.rmtree(self.tmp)
        if self.old_home is not None:
            os.environ["HOME"] = self.old_home

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = om.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def note(self, rel):
        return (self.locker / rel).read_text()


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


if __name__ == "__main__":
    unittest.main()
