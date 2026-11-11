"""Tests for viewer/omalocker-viewer, end to end with `omalocker push`.
Fictional people only (staging). Run: make test"""

import contextlib
import http.cookiejar
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


vw = load("omalocker_viewer", REPO / "viewer" / "omalocker-viewer")
om = load("omalocker_cli", REPO / "bin" / "omalocker")

STUDENT = "rowan@student.example.org"
PEOPLE = {
    "parent": "parent.primary@example.org",
    "other_parent": "parent.other@example.org",
    "biology": "okafor@example.org",
    "advisor": "pell@example.org",
    "coach": "ibarra@example.org",
    "admin": "office@example.org",
    "nobody": "nobody@example.org",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Viewer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {k: os.environ.pop(k) for k in list(os.environ)
                      if k.startswith(("XDG_", "OMALOCKER_"))}
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp)
        os.environ["OMALOCKER_VIEWER_QUIET"] = "1"
        os.environ["OMALOCKER_BACKUP_CONFIG"] = str(self.tmp / "backup.toml")
        self.data = self.tmp / "viewer"
        self.admin("init", "--env", "staging", "--base-url", "http://127.0.0.1")
        self.server = vw.make_server(self.data, "127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

        self.admin("person", "add", "--name", "Rowan Teague", "--email", STUDENT,
                   "--student", "--grad-year", "2029")
        for key, email in PEOPLE.items():
            extra = ["--admin"] if key == "admin" else []
            self.admin("person", "add", "--name", key.replace("_", " ").title(),
                       "--email", email, *extra)
        self.admin("grant", "parent", "--person", PEOPLE["parent"], "--student", STUDENT,
                   "--primary-custody")
        self.admin("grant", "parent", "--person", PEOPLE["other_parent"], "--student", STUDENT)
        self.admin("grant", "teacher", "--person", PEOPLE["biology"], "--student", STUDENT,
                   "--scope", "Biology")
        self.admin("grant", "advisor", "--person", PEOPLE["advisor"], "--student", STUDENT)
        self.admin("grant", "activity", "--person", PEOPLE["coach"], "--student", STUDENT,
                   "--scope", "Cross Country")

        self.locker = self.tmp / "Locker"
        shutil.copytree(REPO / "fixtures" / "sample-locker", self.locker)
        token = self.admin("push-token", STUDENT).strip()
        (self.tmp / "push-key").write_text(token + "\n")
        cfg = self.tmp / "viewer.toml"
        cfg.write_text(f'url = "{self.base}"\ntoken_file = "{self.tmp / "push-key"}"\n')
        os.environ["OMALOCKER_VIEWER_CONFIG"] = str(cfg)
        self.student_id = 1

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp)
        for k in [k for k in os.environ if k.startswith(("XDG_", "OMALOCKER_"))]:
            del os.environ[k]
        os.environ.update(self.saved)
        if self.old_home is not None:
            os.environ["HOME"] = self.old_home

    # -- helpers
    def admin(self, *argv, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vw.main(["--data", str(self.data), *argv])
        if ok:
            self.assertEqual(code, 0, err.getvalue())
        return out.getvalue() if ok else (code, err.getvalue())

    def push(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = om.main(["--locker", str(self.locker), "push"])
        return code, out.getvalue(), err.getvalue()

    def browser(self, who=None):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)
        if who:
            link = self.admin("sign-in-link", PEOPLE.get(who, who)).strip()
            token = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["t"][0]
            self.post(opener, "/signin", {"t": token}, expect=303)
        return opener

    def get(self, opener, path):
        try:
            with opener.open(self.base + path) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read().decode()

    def post(self, opener, path, form, expect=None):
        data = urllib.parse.urlencode(form).encode()
        try:
            with opener.open(self.base + path, data=data) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            with e:
                status = e.code
        if expect:
            self.assertEqual(status, expect)
        return status

    def raw_push(self, payload, token=None):
        token = token or (self.tmp / "push-key").read_text().strip()
        req = urllib.request.Request(self.base + "/api/push", data=json.dumps(payload).encode(),
                                     headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def url(self, audience, scope="", note=None):
        u = vw.view_url(self.student_id, audience, scope)
        if note:
            u += "n/" + "/".join(urllib.parse.quote(p, safe="") for p in note.split("/"))
        return u

    # -- tests
    def test_push_then_each_person_sees_only_their_view(self):
        code, out, err = self.push()
        self.assertEqual(code, 0, err)
        self.assertIn("Pushed 8 views", out)

        parent = self.browser("parent")
        status, body = self.get(parent, "/")
        self.assertEqual(status, 200)
        self.assertIn("Rowan Teague", body)
        self.assertIn("Family view", body)
        status, body = self.get(parent, self.url("parent"))
        self.assertEqual(status, 200)
        self.assertIn("as of", body)
        self.assertIn("Pathway/Milestones/2026-11-08 League finals", body)
        self.assertNotIn("Journal/2026-11-10", body)  # not on the first page
        self.assertIn("Show everything", body)
        status, body = self.get(parent, self.url("parent") + "?all=1")
        self.assertIn("Journal/2026-11-10", body)
        self.assertNotIn("ask about summer labs", body)
        self.assertNotIn("Jules Marchetti.md", body)
        self.assertEqual(self.get(parent, self.url("teacher", "Biology"))[0], 404)
        self.assertEqual(self.get(parent, self.url("advisor"))[0], 404)

        teacher = self.browser("biology")
        self.assertEqual(self.get(teacher, self.url("teacher", "Biology"))[0], 200)
        status, body = self.get(teacher, self.url(
            "teacher", "Biology", "Work/Biology/Lab report - yeast respiration.md"))
        self.assertEqual(status, 200)
        for other in (self.url("teacher", "Geometry"), self.url("parent"), self.url("advisor"),
                      self.url("teacher", "Biology", "Work/English 10/Personal essay draft.md")):
            self.assertEqual(self.get(teacher, other)[0], 404, other)

        advisor = self.browser("advisor")
        self.assertEqual(self.get(advisor, self.url("advisor"))[0], 200)
        self.assertEqual(self.get(advisor, self.url("advisor", note="Journal/2026-11-10.md"))[0], 404)

        coach = self.browser("coach")
        self.assertEqual(self.get(coach, self.url("activity", "Cross Country"))[0], 200)
        self.assertEqual(self.get(coach, self.url("activity", "Robotics Club"))[0], 404)

    def test_non_custodial_parent_and_strangers_see_nothing(self):
        self.push()
        other = self.browser("other_parent")
        status, body = self.get(other, "/")
        self.assertIn("Nothing to show yet", body)
        self.assertEqual(self.get(other, self.url("parent"))[0], 404)
        nobody = self.browser("nobody")
        self.assertEqual(self.get(nobody, self.url("parent"))[0], 404)
        anon = self.browser()
        status, _ = self.get(anon, self.url("parent"))
        self.assertEqual(status, 303)

    def test_admin_sees_the_parent_view(self):
        self.push()
        office = self.browser("admin")
        self.assertEqual(self.get(office, self.url("parent"))[0], 200)
        self.assertEqual(self.get(office, self.url("teacher", "Biology"))[0], 404)

    def test_sign_in_link_works_once_and_expires(self):
        link = self.admin("sign-in-link", PEOPLE["parent"]).strip()
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["t"][0]
        # Opening the link doesn't sign in (mail scanners open links); the button does.
        opener = self.browser()
        self.assertEqual(self.get(opener, "/signin?t=" + token)[0], 200)
        self.post(opener, "/signin", {"t": token}, expect=303)
        self.post(self.browser(), "/signin", {"t": token}, expect=400)

        link = self.admin("sign-in-link", PEOPLE["parent"]).strip()
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["t"][0]
        real_clock = vw.clock
        try:
            vw.clock = lambda: real_clock() + vw.SIGN_IN_TTL + 1
            self.post(self.browser(), "/signin", {"t": token}, expect=400)
        finally:
            vw.clock = real_clock

    def test_sign_out_ends_the_session(self):
        self.push()
        parent = self.browser("parent")
        self.assertEqual(self.get(parent, self.url("parent"))[0], 200)
        self.post(parent, "/signout", {}, expect=303)
        self.assertEqual(self.get(parent, self.url("parent"))[0], 303)

    def test_repush_replaces_views(self):
        self.push()
        rel = self.locker / "Journal" / "2026-11-10.md"
        rel.write_text(rel.read_text().replace("type: journal", "type: journal\nshare: [private]", 1))
        self.assertEqual(self.push()[0], 0)
        teacher = self.browser("biology")
        self.assertEqual(self.get(teacher, self.url(
            "teacher", "Biology", "Journal/2026-11-10.md"))[0], 404)

    def test_viewer_refuses_what_no_view_may_hold(self):
        view = {"audience": "parent", "scope": None, "as_of": "2026-11-10T20:00:00+00:00"}
        for path, text in (
                ("Inbox/x.md", "---\ntype: inbox\nshare:\n  - private\n---\nsecret\n"),
                ("Inbox/y.md", "---\ntype: inbox\nshare: [private]\n---\nsecret\n"),
                ("AGENTS.md", "---\ntype: guide\n---\n"),
                ("People/Zz.md", "---\ntype: person\nrole: student\n---\n"),
                ("../etc.md", "---\ntype: inbox\n---\n"),
                (".obsidian/x.md", "---\ntype: inbox\n---\n")):
            status, body = self.raw_push({"views": [{**view, "notes": [
                {"path": path, "type": "x", "summary": False, "text": text}]}]})
            self.assertEqual(status, 422, path)
        status, _ = self.raw_push({"views": [{**view, "notes": []}]}, token="x" * 43)
        self.assertEqual(status, 401)
        # A private milestone is still the parent's to see.
        status, _ = self.raw_push({"views": [{**view, "notes": [{
            "path": "Pathway/Milestones/2026-01-01 A.md", "type": "milestone",
            "summary": True, "text": "---\ntype: milestone\nshare: [private]\n---\n"}]}]})
        self.assertEqual(status, 200)

    def test_note_text_is_escaped(self):
        note = self.locker / "Journal" / "2026-11-10.md"
        note.write_text(note.read_text() + '\n<script>alert(1)</script> <img src=x onerror=y>'
                        '\n[x](javascript:alert(1)) [ok](https://example.org)\n')
        self.push()
        parent = self.browser("parent")
        status, body = self.get(parent, self.url("parent", note="Journal/2026-11-10.md"))
        self.assertEqual(status, 200)
        self.assertNotIn("<script>", body)
        self.assertNotIn("<img", body)
        self.assertNotIn('href="javascript', body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn('href="https://example.org"', body)

    def test_links_only_to_notes_in_the_same_view(self):
        self.push()
        teacher = self.browser("biology")
        status, body = self.get(teacher, self.url("teacher", "Biology", "Journal/2026-11-10.md"))
        self.assertEqual(status, 200)
        # Biology is in this view; English 10's class note and the classmate aren't.
        self.assertRegex(body, r'<a href="[^"]*Classes/Biology\.md">Biology</a>')
        self.assertIn('<span class="unlinked">English 10</span>', body)
        self.assertIn('<span class="unlinked">Jules Marchetti</span>', body)

    def test_staging_takes_test_addresses_only(self):
        code, err = self.admin("person", "add", "--name", "Real", "--email",
                               "someone@gmail.com", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("fictional people only", err)

    def test_push_needs_https_off_this_machine(self):
        cfg = Path(os.environ["OMALOCKER_VIEWER_CONFIG"])
        cfg.write_text(cfg.read_text().replace(self.base, "http://viewer.school.example"))
        code, _, err = self.push()
        self.assertEqual(code, 1)
        self.assertIn("https://", err)

    def test_graduate_lists_then_deletes(self):
        self.push()
        # A sibling still in school keeps parent_two's login; okafor teaches both.
        self.admin("person", "add", "--name", "Sibling", "--email", "sib@student.example.org",
                   "--student", "--grad-year", "2031")
        self.admin("grant", "parent", "--person", PEOPLE["other_parent"],
                   "--student", "sib@student.example.org", "--primary-custody")
        parent = self.browser("parent")
        self.assertEqual(self.get(parent, self.url("parent"))[0], 200)

        out = self.admin("graduate", STUDENT)
        self.assertIn("Nothing deleted", out)
        self.assertIn(PEOPLE["parent"], out)
        self.assertNotIn(PEOPLE["other_parent"], out)
        self.assertEqual(self.get(parent, self.url("parent"))[0], 200)

        out = self.admin("graduate", STUDENT, "--yes")
        self.assertIn("Deleted.", out)
        db = vw.connect(self.data)
        try:
            emails = {r["email"] for r in db.execute("SELECT email FROM people")}
            for table in ("views", "notes", "grants", "push_tokens"):
                n = db.execute(f"SELECT COUNT(*) FROM {table} WHERE student_id = 1").fetchone()[0]
                self.assertEqual(n, 0, table)
        finally:
            db.close()
        self.assertNotIn(STUDENT, emails)
        self.assertNotIn(PEOPLE["parent"], emails)          # only had this student
        self.assertIn(PEOPLE["other_parent"], emails)       # has the sibling
        self.assertIn(PEOPLE["biology"], emails)            # staff stay
        self.assertEqual(self.get(parent, self.url("parent"))[0], 303)  # session gone
        code, _, err = self.push()                          # old push token is dead
        self.assertEqual(code, 1)
        self.assertIn("401", err)
        raw = (self.data / "viewer.db").read_bytes()
        self.assertNotIn(b"Rowan Teague", raw)
        self.assertNotIn(b"yeast respiration", raw)

    def test_graduate_only_students(self):
        code, err = self.admin("graduate", PEOPLE["parent"], "--yes", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("isn't a student", err)

    def test_security_headers(self):
        status, _ = self.get(self.browser(), "/")
        with urllib.request.urlopen(self.base + "/") as r:
            self.assertIn("default-src 'none'", r.headers["Content-Security-Policy"])
            self.assertEqual(r.headers["Cache-Control"], "no-store")
            self.assertEqual(r.headers["Referrer-Policy"], "no-referrer")


class Markdown(unittest.TestCase):
    def test_shapes(self):
        out = vw.render_markdown(
            "---\ntype: work\nclass: \"[[Biology]]\"\n---\n# Title\n\n- a **b**\n- [x] done\n\n"
            "| A | B |\n|---|---|\n| 1 | [[Gone]] |\n\n<!-- omalocker:x -->\n```\n<b>\n```\n",
            lambda t: "/n/Biology.md" if t == "Biology" else None)
        self.assertIn('<a href="/n/Biology.md">Biology</a>', out)
        self.assertIn("<h1>Title</h1>", out)
        self.assertIn("<strong>b</strong>", out)
        self.assertIn("☑ done", out)
        self.assertIn('<td><span class="unlinked">Gone</span></td>', out)
        self.assertIn("<pre><code>&lt;b&gt;</code></pre>", out)
        self.assertNotIn("omalocker:x", out)


if __name__ == "__main__":
    unittest.main()
