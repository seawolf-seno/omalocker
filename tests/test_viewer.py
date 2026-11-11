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
fake_turso = load("fake_turso", REPO / "tests" / "fake_turso.py")
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
    """On a local SQLite file. ViewerOnTurso runs the same tests through the Turso client."""
    REMOTE = False

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {k: os.environ.pop(k) for k in list(os.environ)
                      if k.startswith(("XDG_", "OMALOCKER_", "TURSO_"))}
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp)
        os.environ["OMALOCKER_VIEWER_QUIET"] = "1"
        os.environ["OMALOCKER_BACKUP_CONFIG"] = str(self.tmp / "backup.toml")
        self.data = self.tmp / "viewer"
        self.fake = None
        if self.REMOTE:
            os.environ["TURSO_AUTH_TOKEN"] = "fake-turso-token"
            self.fake = fake_turso.FakeTurso(str(self.tmp / "turso.db"), "fake-turso-token")
            self.target, self.db_args = self.fake.url, ["--db", self.fake.url]
        else:
            self.target, self.db_args = self.data, ["--data", str(self.data)]
        self.admin("init", "--env", "staging", "--base-url", "http://127.0.0.1")
        self.server = vw.make_server(self.target, "127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

        self.admin("person", "add", "--name", "Rowan Teague", "--email", STUDENT,
                   "--student", "--grad-year", "2029", "--blackbaud-id", "BB-ROWAN")
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
        if self.fake:
            self.fake.close()
        shutil.rmtree(self.tmp)
        for k in [k for k in os.environ if k.startswith(("XDG_", "OMALOCKER_", "TURSO_"))]:
            del os.environ[k]
        os.environ.update(self.saved)
        if self.old_home is not None:
            os.environ["HOME"] = self.old_home

    # -- helpers
    def admin(self, *argv, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vw.main([*self.db_args, *argv])
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

    def raw_push(self, payload, token=None, path="/api/push"):
        token = token or (self.tmp / "push-key").read_text().strip()
        req = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(),
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
        # One child, one view: home goes straight there.
        self.assertEqual(self.get(parent, "/")[0], 303)
        status, body = self.get(parent, self.url("parent"))
        self.assertEqual(status, 200)
        self.assertIn("Rowan Teague", body)
        self.assertIn("Updated ", body)
        self.assertIn(">League finals<", body)
        self.assertIn("Nov 8, 2026", body)
        self.assertIn('<span class="level">Developing</span>', body)  # mastery on the overview
        self.assertIn("Mr. Okafor · Room S104 · Block 2A", body)
        self.assertNotIn("Journal/2026-11-10", body)  # not on the first page
        self.assertIn("Show everything", body)
        status, body = self.get(parent, self.url("parent") + "?all=1")
        self.assertIn("Journal/2026-11-10", body)
        self.assertIn(">Nov 10, 2026<", body)
        self.assertNotIn("ask about summer labs", body)
        self.assertNotIn("Jules Marchetti", body)
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
        self.assertIn("Nothing is shared with you yet", body)
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

    def test_demo_link_lasts_the_hours_asked_on_staging_only(self):
        def token_of(link):
            return urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["t"][0]
        real_clock = vw.clock
        try:
            link = self.admin("sign-in-link", PEOPLE["parent"], "--hours", "48").strip()
            vw.clock = lambda: real_clock() + 47 * 3600
            self.post(self.browser(), "/signin", {"t": token_of(link)}, expect=303)
            vw.clock = real_clock
            link = self.admin("sign-in-link", PEOPLE["parent"], "--hours", "48").strip()
            vw.clock = lambda: real_clock() + 49 * 3600
            self.post(self.browser(), "/signin", {"t": token_of(link)}, expect=400)
        finally:
            vw.clock = real_clock
        code, err = self.admin("sign-in-link", PEOPLE["parent"], "--hours", "100", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("between 1 and 72", err)
        self.assertIn("valid 48h", json.dumps(self.audit_log()))
        db = vw.connect(self.target)
        try:
            db.execute("UPDATE settings SET value = 'production' WHERE key = 'env'")
        finally:
            db.close()
        code, err = self.admin("sign-in-link", PEOPLE["parent"], "--hours", "48", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("staging only", err)

    def outbox(self):
        db = vw.connect(self.target)
        try:
            return [dict(to=r["to_addr"], subject=r["subject"], body=r["body"])
                    for r in db.execute("SELECT * FROM outbox ORDER BY id")]
        finally:
            db.close()

    def ask_for_link(self, email):
        anon = self.browser()
        data = urllib.parse.urlencode({"email": email}).encode()
        with anon.open(self.base + "/signin/email", data=data) as r:
            return r.status, r.read().decode()

    def test_parent_gets_a_link_by_email(self):
        self.push()
        status, body = self.get(self.browser(), "/")
        self.assertIn("Email me a sign-in link", body)
        status, body = self.ask_for_link(PEOPLE["parent"])
        self.assertEqual(status, 200)
        self.assertIn("Check your email", body)
        [mail] = self.outbox()
        self.assertEqual((mail["to"], mail["subject"]), (PEOPLE["parent"], "Your OmaLocker sign-in link"))
        token = re.search(r"/signin\?t=([\w-]+)", mail["body"]).group(1)
        self.assertNotIn("Rowan", mail["body"])   # no student details in email
        parent = self.browser()
        self.post(parent, "/signin", {"t": token}, expect=303)
        self.assertEqual(self.get(parent, self.url("parent"))[0], 200)
        self.assertIn("put a link", self.admin("sign-in-link", PEOPLE["biology"], "--send"))
        self.assertIn(PEOPLE["biology"], self.admin("outbox"))

    def test_link_requests_reveal_nothing_and_are_limited(self):
        _, known = self.ask_for_link(PEOPLE["parent"])
        _, unknown = self.ask_for_link("stranger@example.org")
        _, student = self.ask_for_link(STUDENT)
        strip = lambda b: re.sub(r"<strong>.*?</strong>", "", b)
        self.assertEqual(strip(known), strip(unknown))
        self.assertEqual(strip(known), strip(student))
        self.assertEqual([m["to"] for m in self.outbox()], [PEOPLE["parent"]])
        for _ in range(4):
            self.ask_for_link(PEOPLE["parent"])
        self.assertEqual(len(self.outbox()), vw.LINKS_PER_ADDRESS_PER_HOUR)
        log = [e for e in self.audit_log() if e["action"] == "sign-in-email"]
        self.assertEqual(sum(e["result"] == "ok" for e in log), 3)
        self.assertIn("address limit", [e["detail"] for e in log])
        self.assertNotIn("stranger@example.org", json.dumps(log))  # typos aren't kept
        _, body = self.ask_for_link('<script>x</script>@example.org')
        self.assertNotIn("<script>x", body)

    def test_production_sends_through_resend(self):
        import http.server
        got = []

        class Resend(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                got.append((self.headers.get("Authorization"),
                            json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"id":"x"}')
        fake = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Resend)
        threading.Thread(target=fake.serve_forever, args=(0.05,), daemon=True).start()
        try:
            db = vw.connect(self.target)
            try:
                db.execute("UPDATE settings SET value = 'production' WHERE key = 'env'")
            finally:
                db.close()
            self.server.RequestHandlerClass.viewer.cfg["env"] = "production"  # loaded at start
            self.admin("person", "add", "--name", "Real-looking Parent",
                       "--email", "jordan@fictional-school.org")
            # Not set up yet: nothing is sent and nothing is kept.
            self.ask_for_link("jordan@fictional-school.org")
            self.assertEqual((got, self.outbox()), ([], []))
            failed = [e for e in self.audit_log() if e["action"] == "sign-in-email"][-1]
            self.assertIn("RESEND_API_KEY", failed["detail"])
            os.environ.update(RESEND_API_KEY="re_test", OMALOCKER_MAIL_FROM="OmaLocker <l@fictional-school.org>",
                              OMALOCKER_RESEND_URL=f"http://127.0.0.1:{fake.server_address[1]}/emails")
            self.ask_for_link("jordan@fictional-school.org")
        finally:
            fake.shutdown()
            fake.server_close()
            for k in ("RESEND_API_KEY", "OMALOCKER_MAIL_FROM", "OMALOCKER_RESEND_URL"):
                os.environ.pop(k, None)
        [(auth, mail)] = got
        self.assertEqual(auth, "Bearer re_test")
        self.assertEqual(mail["to"], ["jordan@fictional-school.org"])
        self.assertIn("/signin?t=", mail["text"])
        self.assertEqual(self.outbox(), [])

    def stored_notes(self):
        db = vw.connect(self.target)
        try:
            return sorted((r["audience"], r["scope"], r["path"], r["summary"], r["text"])
                          for r in db.execute("SELECT * FROM notes"))
        finally:
            db.close()

    def test_large_push_goes_in_parts_with_the_same_result(self):
        code, out, _ = self.push()
        self.assertNotIn("parts", out)
        whole = self.stored_notes()
        os.environ["OMALOCKER_PUSH_PART_BYTES"] = "6000"
        code, out, err = self.push()
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"Pushed 8 views \(67 notes\) as of .* in \d+ parts")
        self.assertGreater(int(re.search(r"in (\d+) parts", out).group(1)), 3)
        self.assertEqual(self.stored_notes(), whole)
        self.assertIn("67 notes in parts", json.dumps(self.audit_log()))
        db = vw.connect(self.target)
        try:  # nothing left waiting
            self.assertEqual(db.execute("SELECT COUNT(*) FROM push_staging").fetchone()[0], 0)
        finally:
            db.close()
        teacher = self.browser("biology")
        self.assertEqual(self.get(teacher, self.url(
            "teacher", "Biology", "Work/Biology/Lab report - yeast respiration.md"))[0], 200)

    def test_parts_that_dont_add_up_change_nothing(self):
        self.push()
        before = self.stored_notes()
        view = {"audience": "parent", "scope": None, "as_of": "2026-11-11T00:00:00+00:00"}
        note = {"path": "Me.md", "type": "person", "summary": True, "text": "---\ntype: person\n---\n"}
        status, r = self.raw_push({}, path="/api/push/begin")
        self.assertEqual(status, 200)
        upload = r["upload"]
        self.assertEqual(self.raw_push({"upload": upload, "views": [{**view, "notes": [note]}]},
                                       path="/api/push/part")[0], 200)
        # Says 2 notes, sent 1.
        status, r = self.raw_push({"upload": upload, "views": [{**view, "count": 2}]},
                                  path="/api/push/commit")
        self.assertEqual(status, 422)
        self.assertIn("don't add up", r["error"])
        # A refused note in a part is turned away too.
        bad = {**note, "path": "Inbox/x.md", "text": "---\ntype: inbox\nshare: [private]\n---\n"}
        self.assertEqual(self.raw_push({"upload": upload, "views": [{**view, "notes": [bad]}]},
                                       path="/api/push/part")[0], 422)
        self.assertEqual(self.stored_notes(), before)
        # Another student's token can't touch this upload.
        self.admin("person", "add", "--name", "Other", "--email", "other@student.example.org",
                   "--student")
        other = self.admin("push-token", "other@student.example.org").strip()
        status, r = self.raw_push({"upload": upload, "views": [{**view, "count": 1}]},
                                  token=other, path="/api/push/commit")
        self.assertEqual(status, 422)
        self.assertIn("unknown or expired upload", r["error"])
        self.assertEqual(self.stored_notes(), before)
        # Graduation clears what was left waiting.
        self.admin("graduate", STUDENT, "--yes")
        db = vw.connect(self.target)
        try:
            for table in ("push_staging", "push_uploads"):
                self.assertEqual(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
        finally:
            db.close()

    def teacher_classes(self):
        """A fictional teacher's OmaMastery folder: one Biology class, three students."""
        bio = self.tmp / "teacher" / "Classes" / "bio"
        bio.mkdir(parents=True)
        (bio / "class.toml").write_text('name = "Biology"\nday = "A"\nblock = 2\nroom = "S210"\n'
                                        'canvas_course = "901"\n')
        (bio / "ideas.toml").write_text(
            '[[idea]]\nname = "Feedback loops in ecosystems"\njoint = "Systems and feedback"\n'
            '[[idea]]\nname = "Cellular respiration"\n')
        (bio / "plan.toml").write_text(
            '[[objective]]\nid = "o1"\ntitle = "Trace energy in a food web"\n'
            'idea = "Feedback loops in ecosystems"\nweek = "1"\n'
            '[[objective]]\nid = "o2"\ntitle = "Model a predator-prey loop"\n'
            'idea = "Feedback loops in ecosystems"\nweek = "2026-11-09"\ncanvas_assignment = "5501"\n'
            '[[objective]]\nid = "o3"\ntitle = "Measure yeast respiration"\n'
            'idea = "Cellular respiration"\nweek = "2026-11-16"\ncanvas_assignment = "5502"\n')
        (bio / "roster.toml").write_text(
            '[[student]]\nname = "Zz Fictional Rowan"\nblackbaud_id = "BB-ROWAN"\n'
            '[[student]]\nname = "Zz Fictional Other"\nblackbaud_id = "BB-OTHER"\n'
            '[[student]]\nname = "Zz Fictional Noid"\n')
        (bio / "mastery.csv").write_text(
            "date,student,objective,level,evidence\n"
            "2026-11-01,Zz Fictional Rowan,o1,Proficient,\n"
            "2026-11-03,Zz Fictional Rowan,o2,Beginning,\n"
            "2026-11-05,Zz Fictional Rowan,o2,Developing,\n"   # latest wins
            "2026-11-06,Zz Fictional Rowan,o3,Extending,\n"
            "2026-11-06,Zz Fictional Other,o1,Not yet,\n"
            "2026-11-06,Zz Fictional Noid,o1,Beginning,\n")
        return bio.parent

    def as_device(self, token, *argv):
        cfg = self.tmp / f"device-{abs(hash(token))}.toml"
        key = cfg.with_suffix(".key")
        key.write_text(token + "\n")
        cfg.write_text(f'url = "{self.base}"\ntoken_file = "{key}"\n')
        saved = os.environ["OMALOCKER_VIEWER_CONFIG"]
        os.environ["OMALOCKER_VIEWER_CONFIG"] = str(cfg)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = om.main(list(argv))
        finally:
            os.environ["OMALOCKER_VIEWER_CONFIG"] = saved
        return code, out.getvalue(), err.getvalue()

    def test_teacher_levels_reach_the_student_and_the_parent(self):
        classes = self.teacher_classes()
        self.admin("person", "add", "--name", "Other", "--email", "other@student.example.org",
                   "--student", "--blackbaud-id", "BB-OTHER")
        code, err = self.admin("push-token", PEOPLE["advisor"], ok=False)
        self.assertEqual(code, 1)                       # no teacher grants: no token
        self.assertIn("no teacher grants", err)
        teacher_token = self.admin("push-token", PEOPLE["biology"]).strip()
        teacher_locker = self.tmp / "teacher" / "Locker"
        code, out, err = self.as_device(teacher_token, "--locker", str(teacher_locker),
                                        "send-levels", "--classes", str(classes))
        self.assertEqual(code, 0, err)
        self.assertIn("1 classes: 1 students stored", out)
        self.assertIn("1 matched a student you have no teacher grant for", out)
        self.assertIn("1 students have no Blackbaud or Canvas id", out)
        db = vw.connect(self.target)
        try:
            stored = [dict(class_=r["class"], data=json.loads(r["data"]))
                      for r in db.execute("SELECT * FROM levels")]
            dump = json.dumps([list(r) for r in db.execute("SELECT * FROM levels")])
        finally:
            db.close()
        self.assertNotIn("Zz", dump)                     # names never left the laptop
        [row] = stored
        ideas = {i["name"]: i["level"] for i in row["data"]["ideas"]}
        self.assertEqual(ideas, {"Feedback loops in ecosystems": "Developing",   # lowest of o1,o2
                                 "Cellular respiration": "Extending"})

        # The student's laptop pulls its own levels, then pushes; the parent sees them.
        student_token = (self.tmp / "push-key").read_text().strip()
        code, out, err = self.as_device(student_token, "--locker", str(self.locker), "pull-levels")
        self.assertEqual(code, 0, err)
        note = (self.locker / "Mastery" / "Biology.md").read_text()
        self.assertIn("| [[Cellular respiration]] | Extending |", note)
        self.assertIn("| Model a predator-prey loop | [[Feedback loops in ecosystems]] | Developing |", note)
        self.assertIn("Copied from [[Mr. Okafor]]", note)   # the student's own text stays
        # The class note follows the teacher's room (OmaMastery/OmaClass): S104 -> S210.
        cls = (self.locker / "Classes" / "Biology.md").read_text()
        props, _ = om.read_note(self.locker / "Classes" / "Biology.md")
        self.assertEqual((props["room"], props["block"], props["day"]), ("S210", "2", "A"))
        self.assertEqual(props["teacher"], "[[Mr. Okafor]]")
        self.assertIn("energy in, energy out", cls)          # the student's notes stay
        self.assertEqual(self.as_device(student_token, "--locker", str(self.locker),
                                        "pull-levels")[1].split("; ")[1].strip(), "0 notes changed")
        self.push()
        parent = self.browser("parent")
        status, body = self.get(parent, self.url("parent"))
        self.assertIn("Extending", body)
        self.assertNotIn("Model a predator-prey loop", body)   # objectives only inside the note
        log = json.dumps(self.audit_log())
        self.assertIn("1 students, 0 unmatched, 1 not theirs", log)
        self.assertIn("levels-pull", log)

        # A teacher can't pull, a student can't send, and graduation clears levels.
        self.assertEqual(self.raw_push({"classes": []}, token=student_token, path="/api/levels")[0], 401)
        self.admin("graduate", STUDENT, "--yes")
        db = vw.connect(self.target)
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM levels WHERE student_id = 1").fetchone()[0], 0)
        finally:
            db.close()

    def test_canvas_assignments_become_work_notes(self):
        os.environ["OMALOCKER_CANVAS_URL"] = "https://pacifica.instructure.com"
        classes = self.teacher_classes()
        teacher_token = self.admin("push-token", PEOPLE["biology"]).strip()
        student_token = (self.tmp / "push-key").read_text().strip()
        send = lambda: self.as_device(teacher_token, "--locker", str(self.tmp / "teacher" / "Locker"),
                                      "send-levels", "--classes", str(classes))
        pull = lambda: self.as_device(student_token, "--locker", str(self.locker), "pull-levels")
        self.assertEqual(send()[0], 0)
        self.assertEqual(pull()[0], 0)
        stub = self.locker / "Work" / "Biology" / "Model a predator-prey loop.md"
        props, body = om.read_note(stub)
        url = "https://pacifica.instructure.com/courses/901/assignments/5501"
        self.assertEqual(props, {"type": "work", "class": "[[Biology]]", "status": "idea",
                                 "ideas": ["[[Feedback loops in ecosystems]]"], "canvas_assignment": url})
        self.assertIn(f"Canvas assignment, week of 2026-11-09: {url}", body)
        self.assertTrue((self.locker / "Work" / "Biology" / "Measure yeast respiration.md").exists())
        # The student writes; the teacher renames the assignment. Same note, writing kept.
        stub.write_text(stub.read_text().replace("status: idea", "status: draft")
                        + "\nFoxes and rabbits, a loop I can graph.\n")
        plan = classes / "bio" / "plan.toml"
        plan.write_text(plan.read_text().replace("Model a predator-prey loop", "Predator-prey model"))
        send(); pull()
        self.assertFalse((self.locker / "Work" / "Biology" / "Predator-prey model.md").exists())
        props, body = om.read_note(stub)
        self.assertEqual(props["status"], "draft")
        self.assertIn("a loop I can graph", body)
        # What goes to Canvas is just the writing; the stub's link is what turned-in needs.
        code, out, _ = self.as_device(student_token, "submission", str(stub))
        self.assertNotIn("Canvas assignment", out)
        self.assertIn("a loop I can graph", out)
        code, _, err = self.as_device(student_token, "--locker", str(self.locker),
                                      "turned-in", str(stub), "--assignment", url)
        self.assertEqual(code, 0, err)
        # The viewer refuses an assignment link that isn't Canvas.
        bad = {"classes": [{"class": "Biology", "as_of": "", "students": [],
                            "info": {"assignments": [{"title": "x", "url": "https://evil.example/x"}]}}]}
        status, r = self.raw_push(bad, token=teacher_token, path="/api/levels")
        self.assertEqual(status, 422)
        self.assertIn("Canvas assignment", r["error"])

    # -- security review (2026-11-10)
    def test_parents_see_the_teachers_levels_not_the_students_copy(self):
        mastery = self.locker / "Mastery" / "Biology.md"
        mastery.write_text(mastery.read_text().replace("| Developing |", "| Extending |"))
        self.push()
        parent = self.browser("parent")
        _, body = self.get(parent, self.url("parent"))
        self.assertIn("no levels from the teacher yet", body)   # honest about the source
        classes = self.teacher_classes()
        token = self.admin("push-token", PEOPLE["biology"]).strip()
        self.as_device(token, "--locker", str(self.tmp / "teacher" / "Locker"),
                       "send-levels", "--classes", str(classes))
        mastery.write_text(mastery.read_text().replace("| Proficient |", "| Extending |"))
        self.push()                                                # student's copy is forged
        _, body = self.get(parent, self.url("parent"))
        levels = re.findall(r'<span>([^<]*)</span><span class="level">([^<]*)</span>', body)
        self.assertEqual(dict(levels), {"Feedback loops in ecosystems": "Developing",
                                        "Cellular respiration": "Extending"})
        _, page_ = self.get(parent, self.url("parent", note="Mastery/Biology.md"))
        self.assertIn("Model a predator-prey loop", page_)     # teacher's targets, not the copy
        self.assertNotIn("Copied from", page_)

    def test_forms_only_from_this_site(self):
        link = self.admin("sign-in-link", PEOPLE["parent"]).strip()
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["t"][0]
        for headers in ({"Sec-Fetch-Site": "cross-site"}, {"Origin": "https://evil.example"}):
            req = urllib.request.Request(self.base + "/signin", headers=headers,
                                         data=urllib.parse.urlencode({"t": token}).encode())
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req)
            self.assertEqual(e.exception.code, 403)
            e.exception.close()
        own = urllib.request.Request(self.base + "/signin/email", headers={
            "Origin": self.base, "Sec-Fetch-Site": "same-origin"},
            data=urllib.parse.urlencode({"email": PEOPLE["parent"]}).encode())
        with urllib.request.urlopen(own) as r:
            self.assertEqual(r.status, 200)
        self.post(self.browser(), "/signin", {"t": token}, expect=303)   # link still unused

    def test_refusals_nobody_signed_in_for_dont_flood_the_log(self):
        for _ in range(5):
            self.raw_push({"views": []}, token="z" * 43)
            self.post(self.browser(), "/signin", {"t": "y" * 43})
        log = self.audit_log("--denied")
        self.assertEqual(len([e for e in log if e["action"] == "push"]), 1)
        self.assertEqual(len([e for e in log if e["action"] == "sign-in"]), 1)

    def test_a_nul_in_a_note_doesnt_break_the_page(self):
        note = self.locker / "Journal" / "2026-11-10.md"
        note.write_text(note.read_text() + "\nodd \x007\x00 bytes [x](https://example.org)\n")
        self.push()
        status, body = self.get(self.browser("parent"), self.url("parent", note="Journal/2026-11-10.md"))
        self.assertEqual(status, 200)
        self.assertIn("odd 7 bytes", body)

    def test_one_upload_cant_stage_without_limit(self):
        view = {"audience": "parent", "scope": None, "as_of": "x"}
        upload = self.raw_push({}, path="/api/push/begin")[1]["upload"]
        notes = [{"path": f"Journal/n{i}.md", "text": "---\ntype: journal\n---\nhi\n"} for i in range(3)]
        old = vw.MAX_STAGED_NOTES
        vw.MAX_STAGED_NOTES = 4
        try:
            self.assertEqual(self.raw_push({"upload": upload, "views": [{**view, "notes": notes}]},
                                           path="/api/push/part")[0], 200)
            status, r = self.raw_push({"upload": upload, "views": [{**view, "notes": [
                {"path": "Journal/x.md", "text": "a"}, {"path": "Journal/y.md", "text": "b"}]}]},
                path="/api/push/part")
        finally:
            vw.MAX_STAGED_NOTES = old
        self.assertEqual(status, 422)
        self.assertIn("too big", r["error"])

    def test_viewer_refuses_private_in_any_yaml_list_style(self):
        view = {"audience": "parent", "scope": None, "as_of": "x"}
        status, _ = self.raw_push({"views": [{**view, "notes": [
            {"path": "Inbox/z.md", "text": "---\ntype: inbox\nshare:\n- private\n---\nsecret\n"}]}]})
        self.assertEqual(status, 422)

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
        db = vw.connect(self.target)
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
        if not self.REMOTE:  # Turso: see docs/viewer.md on deleted data and backups
            raw = (self.data / "viewer.db").read_bytes()
            self.assertNotIn(b"Rowan Teague", raw)
            self.assertNotIn(b"yeast respiration", raw)

    def audit_log(self, *argv):
        return json.loads(self.admin("audit", "--json", *argv))

    def test_access_log_records_opens_refusals_and_changes(self):
        self.push()
        teacher = self.browser("biology")
        self.get(teacher, self.url("teacher", "Biology"))
        self.get(teacher, self.url("teacher", "Biology", "Journal/2026-11-10.md"))
        self.get(teacher, self.url("parent"))                       # not theirs
        self.post(self.browser(), "/signin", {"t": "x" * 43}, expect=400)

        mine = self.audit_log("--person", PEOPLE["biology"])
        self.assertEqual([(e["action"], e["audience"], e["path"], e["result"]) for e in mine], [
            ("sign-in", "", "", "ok"),
            ("open", "teacher", "", "ok"),
            ("open", "teacher", "Journal/2026-11-10.md", "ok"),
            ("open", "parent", "", "denied"),
        ])
        self.assertTrue(all(e["actor"] == PEOPLE["biology"] for e in mine))
        self.assertEqual(mine[1]["student"], STUDENT)

        everything = self.audit_log()
        actions = [e["action"] for e in everything]
        for action in ("person-add", "grant", "push-token", "push", "sign-in-link"):
            self.assertIn(action, actions)
        self.assertTrue(all(e["actor"].startswith("cli") for e in everything
                            if e["action"] in ("grant", "person-add")))
        push = [e for e in everything if e["action"] == "push"][0]
        self.assertEqual((push["student"], push["detail"]), (STUDENT, "8 views, 67 notes"))
        denied = self.audit_log("--denied")
        self.assertEqual({(e["action"], e["result"]) for e in denied},
                         {("open", "denied"), ("sign-in", "denied")})

        self.raw_push({"views": []}, token="y" * 43)
        self.raw_push({"views": [{"audience": "parent", "as_of": "x", "notes": [
            {"path": "AGENTS.md", "text": "---\ntype: guide\n---\n"}]}]})
        refused = [e for e in self.audit_log("--denied") if e["action"] == "push"]
        self.assertEqual([e["result"] for e in refused], ["denied", "refused"])
        self.assertIn("AGENTS.md", refused[1]["detail"])

        text = self.admin("audit", "--student", STUDENT)
        self.assertIn("Journal/2026-11-10.md", text)
        self.assertIn("DENIED", text)

    def test_graduation_removes_the_student_from_the_log(self):
        self.push()
        parent = self.browser("parent")
        self.get(parent, self.url("parent"))
        self.assertTrue(self.audit_log("--student", STUDENT))
        self.admin("graduate", STUDENT, "--yes")
        log = self.audit_log("--limit", "1000")
        dump = json.dumps(log)
        for gone in (STUDENT, PEOPLE["parent"], PEOPLE["other_parent"]):
            self.assertNotIn(gone, dump)
        self.assertFalse([e for e in log if e["student"]])
        self.assertIn(PEOPLE["biology"], dump)   # staff still in the log (their grant line went)
        last = log[-1]
        self.assertEqual(last["action"], "graduate")
        self.assertRegex(last["detail"], r"student #1: .* \d+ access-log entries deleted")
        if not self.REMOTE:
            raw = (self.data / "viewer.db").read_bytes()
            self.assertNotIn(STUDENT.encode(), raw)
            self.assertNotIn(PEOPLE["parent"].encode(), raw)

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


class ViewerOnTurso(Viewer):
    """Every viewer test again, with the database behind Turso's HTTP API (a fake)."""
    REMOTE = True

    def test_settings_come_from_the_database(self):
        code, err = self.admin("init", "--env", "production", "--base-url", "https://x", ok=False)
        self.assertEqual(code, 0, err)  # already set up: settings unchanged
        self.assertIn("staging", self.admin("list"))

    def test_vercel_entry_point_serves_from_turso(self):
        import http.server
        os.environ["TURSO_DATABASE_URL"] = self.fake.url
        entry = load("vercel_entry", REPO / "api" / "index.py")
        self.assertTrue(issubclass(entry.handler, http.server.BaseHTTPRequestHandler))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), entry.handler)
        threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True).start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            with urllib.request.urlopen(base + "/") as r:
                self.assertIn("Test version", r.read().decode())
            with urllib.request.urlopen(base + "/style.css") as r:
                self.assertEqual(r.headers["Content-Type"], "text/css; charset=utf-8")
        finally:
            server.shutdown()
            server.server_close()

    def test_bad_database_token_fails_clearly(self):
        os.environ["TURSO_AUTH_TOKEN"] = "wrong"
        code, err = self.admin("list", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("401", err)


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
