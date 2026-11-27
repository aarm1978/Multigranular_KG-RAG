"""Serve or export one portable, loopback-only exploratory reviewer session."""
from __future__ import annotations

import argparse
import hashlib
from http.server import HTTPServer
import json
from pathlib import Path
import sqlite3
import time

if __package__:
    from .http_local import review_handler
else:
    from http_local import review_handler

ASSETS = {
    "/": ("index.html", "text/html"),
    "/style.css": ("style.css", "text/css"),
    "/app.js": ("app.js", "text/javascript"),
    "/save_coordinator.js": ("save_coordinator.js", "text/javascript"),
}
CHOICES = ("Supported", "Unsupported", "Insufficient evidence")


class Session:
    """Bind a transactional local record to one exact blinded package."""

    def __init__(self, directory, now=time.time):
        raw = (directory / "cases.json").read_bytes()
        self.hash = hashlib.sha256(raw).hexdigest()
        manifest = json.loads((directory / "package-manifest.json").read_bytes())
        for name, expected in manifest["files"].items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Reviewer package drift: " + name)
        data = json.loads(raw)
        self.now, self.evaluator, self.purpose = now, data["evaluator"], data["purpose"]
        self.cases = {c["id"]: c for c in data["cases"]}
        self.db = sqlite3.connect(directory / "session.sqlite")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS session (id INTEGER PRIMARY KEY, data TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS edits (at REAL, case_id TEXT, answer TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS transitions (at REAL, case_id TEXT, action TEXT)"
        )
        initial = dict(
            package=self.hash,
            revision=0,
            cursor=next(iter(self.cases)),
            running=False,
            last=None,
            records={
                k: dict(
                    judgment=None,
                    comment="",
                    problematic="",
                    completeReview=False,
                    visits=0,
                    elapsedSeconds=0.0,
                    activeSeconds=0.0,
                )
                for k in self.cases
            },
        )
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO session VALUES(1,?)", (json.dumps(initial),)
            )
        if self.state()["package"] != self.hash:
            raise ValueError("Session belongs to a different package")

    def state(self):
        """Read the last committed cursor and all answers, including unfinished cases."""
        return json.loads(
            self.db.execute("SELECT data FROM session WHERE id=1").fetchone()[0]
        )

    def unit(self, case):
        """Return the blinded case bound to the neutral alias."""
        if case not in self.cases:
            raise ValueError("Unknown case")
        return self.cases[case]

    def change(self, event):
        """Persist one revision atomically with its timing and optional judgment change."""
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            s = self.state()
            if (
                event.get("revision") != s["revision"]
                or event.get("sourceUnitID") != s["cursor"]
            ):
                raise ValueError(
                    "Session changed in another tab. Reload before continuing."
                )
            now = self.now()
            kind = event["type"]
            case = s["cursor"]
            row = s["records"][case]
            if kind == "open":
                s["running"] = True
                row["visits"] += 1
            elif not s["running"]:
                raise ValueError("Resume the session first")
            else:
                seconds = max(0.0, now - s["last"])
                # An interrupted heartbeat cannot measure the intervening time.
                if seconds <= 20:
                    row["elapsedSeconds"] += seconds
                    row["activeSeconds"] += min(
                        seconds, max(0.0, float(event.get("activeSeconds", 0)))
                    )
                if kind == "save":
                    answer = {
                        k: event[k]
                        for k in (
                            "judgment",
                            "completeReview",
                            "comment",
                            "problematic",
                        )
                    }
                    if (
                        answer["judgment"] not in (*CHOICES, None)
                        or type(answer["completeReview"]) is not bool
                    ):
                        raise ValueError("Unknown judgment or confirmation")
                    if (
                        self.cases[case]["phase"] == "Identity"
                        and answer["judgment"] == "Supported"
                        and not answer["completeReview"]
                    ):
                        raise ValueError(
                            "Supported requires review of the complete identity group"
                        )
                    if not all(
                        isinstance(answer[k], str) for k in ("comment", "problematic")
                    ):
                        raise ValueError("Comments must be text")
                    if any(row[k] != v for k, v in answer.items()):
                        row.update(answer)
                        self.db.execute(
                            "INSERT INTO edits VALUES(?,?,?)",
                            (now, case, json.dumps(answer)),
                        )
                elif kind == "go":
                    target = event["target"]
                    self.unit(target)
                    if target != case:
                        s["cursor"] = target
                        s["records"][target]["visits"] += 1
                elif kind == "pause":
                    s["running"] = False
                elif kind != "tick":
                    raise ValueError("Unknown session action")
            if kind in ("open", "go", "pause"):
                self.db.execute(
                    "INSERT INTO transitions VALUES(?,?,?)", (now, s["cursor"], kind)
                )
            s.update(revision=s["revision"] + 1, last=now)
            self.db.execute("UPDATE session SET data=? WHERE id=1", (json.dumps(s),))
        return s

    def export(self):
        """Export one consistent snapshot, including unanswered cases and edit history."""
        with self.db:
            self.db.execute("BEGIN")
            s = self.state()
            rows = [
                dict(
                    case=k,
                    phase=self.cases[k]["phase"],
                    revisits=max(0, v["visits"] - 1),
                    inactiveSeconds=v["elapsedSeconds"] - v["activeSeconds"],
                    **v,
                )
                for k, v in s["records"].items()
            ]
            edits = [
                dict(unixTime=t, case=c, **json.loads(a))
                for t, c, a in self.db.execute(
                    "SELECT at,case_id,answer FROM edits ORDER BY rowid"
                )
            ]
            transitions = [
                dict(unixTime=t, case=c, action=a)
                for t, c, a in self.db.execute(
                    "SELECT at,case_id,action FROM transitions ORDER BY rowid"
                )
            ]
        summary = dict(
            cases=len(rows),
            answered=sum(r["judgment"] is not None for r in rows),
            elapsedSeconds=sum(r["elapsedSeconds"] for r in rows),
            activeSeconds=sum(r["activeSeconds"] for r in rows),
        )
        return json.dumps(
            dict(
                evaluator=self.evaluator,
                purpose=self.purpose,
                packageSha256=self.hash,
                revision=s["revision"],
                cursor=s["cursor"],
                summary=summary,
                cases=rows,
                edits=edits,
                transitions=transitions,
            ),
            indent=2,
            ensure_ascii=False,
        ).encode()


def main():
    """Start/resume beside cases.json, or export the durable local snapshot."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("serve", "export"))
    p.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--port", type=int, default=8794)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    session = Session(a.package)
    try:
        if a.mode == "export":
            if a.output:
                # Exclusive creation protects earlier exports and the session itself.
                with a.output.open("xb") as f:
                    f.write(session.export() + b"\n")
            else:
                print(session.export().decode())
        else:
            handler = review_handler(session, a.package / "static", ASSETS)
            with HTTPServer(("127.0.0.1", a.port), handler) as server:
                print(f"Open http://127.0.0.1:{server.server_port}", flush=True)
                server.serve_forever()
    finally:
        session.db.close()


if __name__ == "__main__":
    main()
