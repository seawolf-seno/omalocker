"""A stand-in for Turso's HTTP API (Hrana v2 /v2/pipeline), backed by a SQLite file.
Enough of the protocol for omalocker-viewer's TursoConnection: execute, sequence,
close, batons (one SQLite connection per stream), bearer token. Tests only."""

import base64
import http.server
import json
import secrets
import sqlite3
import threading


def encode(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, bytes):
        return {"type": "blob", "base64": base64.b64encode(v).decode()}
    return {"type": "text", "value": v}


def decode(a):
    kind = a.get("type")
    if kind == "integer":
        return int(a["value"])
    if kind == "float":
        return float(a["value"])
    if kind == "text":
        return a["value"]
    if kind == "blob":
        return base64.b64decode(a["base64"])
    return None


class FakeTurso:
    def __init__(self, path, token):
        self.path, self.token = path, token
        self.streams, self.lock = {}, threading.Lock()
        self.requests = 0
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                fake.requests += 1
                if self.headers.get("Authorization") != f"Bearer {fake.token}":
                    self.send_response(401)
                    self.end_headers()
                    return
                if self.path != "/v2/pipeline":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                out = json.dumps(fake.pipeline(body)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def pipeline(self, body):
        baton = body.get("baton")
        with self.lock:
            conn = self.streams.pop(baton, None) if baton else None
        if conn is None:
            conn = sqlite3.connect(self.path, isolation_level=None, timeout=10,
                                   check_same_thread=False)
        results, open_ = [], True
        for req in body.get("requests", []):
            try:
                if req["type"] == "execute":
                    stmt = req["stmt"]
                    cur = conn.execute(stmt["sql"], [decode(a) for a in stmt.get("args", [])])
                    rows = cur.fetchall()
                    cols = [{"name": d[0]} for d in (cur.description or [])]
                    results.append({"type": "ok", "response": {"type": "execute", "result": {
                        "cols": cols, "rows": [[encode(v) for v in r] for r in rows],
                        "affected_row_count": max(cur.rowcount, 0),
                        "last_insert_rowid": str(cur.lastrowid) if cur.lastrowid else None}}})
                elif req["type"] == "sequence":
                    conn.executescript(req["sql"])
                    results.append({"type": "ok", "response": {"type": "sequence"}})
                elif req["type"] == "close":
                    conn.close()
                    open_ = False
                    results.append({"type": "ok", "response": {"type": "close"}})
            except sqlite3.Error as e:
                results.append({"type": "error", "error": {"message": f"SQLite error: {e}"}})
        new_baton = None
        if open_:
            new_baton = secrets.token_hex(8)
            with self.lock:
                self.streams[new_baton] = conn
        return {"baton": new_baton, "base_url": None, "results": results}

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        with self.lock:
            for conn in self.streams.values():
                conn.close()
            self.streams.clear()
