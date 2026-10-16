"""Claims, findings and Confirm/Dismiss state for one case.

SQLite runs in memory. Every change is serialized and saved into the vault as an
encrypted blob, so no plaintext database file ever exists.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from .omissions import omission_code

BLOB = "findings"
STATES = ("open", "confirmed", "dismissed")
SCHEMA = """
CREATE TABLE claims (
    id INTEGER PRIMARY KEY, doc TEXT, page INTEGER, para INTEGER,
    status TEXT CHECK (status IN ('verified', 'rejected')), reason TEXT, claim TEXT);
CREATE TABLE findings (
    key TEXT PRIMARY KEY, kind TEXT, state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'confirmed', 'dismissed')),
    stale INTEGER NOT NULL DEFAULT 0, payload TEXT, updated TEXT);
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cite(c):
    return [c["doc"], c["page"], c["para"]]


def _key(*parts):
    # Stable id: the same finding gets the same key on every re-run, so decisions survive
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16]


class Store:
    def __init__(self, vault, db):
        self.vault, self.db = vault, db

    @classmethod
    def open(cls, vault):
        db = sqlite3.connect(":memory:", check_same_thread=False)  # callers hold a lock; the API uses worker threads
        blob = vault.get_blob(BLOB)
        if blob:
            db.deserialize(blob)
        else:
            db.executescript(SCHEMA)
        return cls(vault, db)

    def _save(self):
        self.db.commit()
        self.vault.put_blob(BLOB, self.db.serialize())

    def save_analysis(self, good, rejected, contradictions, omissions, docs):
        # Replace the claims. Keep each finding's state if it comes back; mark the rest stale.
        db = self.db
        db.execute("DELETE FROM claims")
        db.executemany(
            "INSERT INTO claims (doc, page, para, status, reason, claim) VALUES (?,?,?,?,?,?)",
            [(c["doc"], c["page"], c["para"], "verified", None, json.dumps(c)) for c in good]
            + [(c["doc"], c["page"], c["para"], "rejected", r, json.dumps(c)) for c, r in rejected])
        db.execute("UPDATE findings SET stale = 1")
        found = []
        for a, b, fields in contradictions:
            w = docs[a["doc"]]["witness"]
            found.append((_key("contradiction", w, a["event"], sorted(fields), sorted([_cite(a), _cite(b)])),
                          "contradiction", {"witness": w, "fields": fields, "a": a, "b": b}))
        for material, w, label, c in omissions:
            kind = omission_code(label)
            found.append((_key("omission", w, c["event"], kind, _cite(c)),
                          "omission", {"witness": w, "kind": kind, "material": material, "claim": c}))
        db.executemany(
            "INSERT INTO findings (key, kind, payload, updated) VALUES (?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, stale = 0",
            [(k, kind, json.dumps(p), _now()) for k, kind, p in found])
        self._save()

    def findings(self, include_stale=False):
        rows = self.db.execute(
            "SELECT key, kind, state, stale, payload, updated FROM findings "
            + ("" if include_stale else "WHERE stale = 0 ") + "ORDER BY kind, rowid").fetchall()
        return [{"key": k, "kind": kind, "state": s, "stale": bool(st), "updated": u, **json.loads(p)}
                for k, kind, s, st, p, u in rows]

    def claims(self, status=None):
        rows = self.db.execute("SELECT status, reason, claim FROM claims WHERE ? IS NULL OR status = ? ORDER BY id",
                               (status, status)).fetchall()
        return [{"status": s, "reason": r, **json.loads(c)} for s, r, c in rows]

    def set_state(self, key, state):
        if state not in STATES:
            raise ValueError(f"state must be one of {STATES}")
        cur = self.db.execute("UPDATE findings SET state = ?, updated = ? WHERE key = ?", (state, _now(), key))
        if cur.rowcount == 0:
            raise KeyError(key)
        self._save()

    def counts(self):
        one = lambda sql: self.db.execute(sql).fetchone()[0]
        return {
            "verified": one("SELECT COUNT(*) FROM claims WHERE status = 'verified'"),
            "rejected": one("SELECT COUNT(*) FROM claims WHERE status = 'rejected'"),
            "contradictions": one("SELECT COUNT(*) FROM findings WHERE kind = 'contradiction' AND stale = 0"),
            "omissions": one("SELECT COUNT(*) FROM findings WHERE kind = 'omission' AND stale = 0"),
        }
