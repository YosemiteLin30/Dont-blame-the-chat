"""SQLite storage for play sessions and chat events."""
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    ended_at REAL,
    result TEXT,
    digits_found INTEGER DEFAULT 0,
    seconds REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts REAL NOT NULL,
    source TEXT,
    user TEXT,
    command TEXT,
    accepted INTEGER,
    message TEXT
);
"""


class SessionDB:
    """Owned by the game thread; the panel reads history through read_recent()."""

    def __init__(self, path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def start_session(self):
        cur = self.conn.execute("INSERT INTO sessions (started_at) VALUES (?)", (time.time(),))
        self.conn.commit()
        return cur.lastrowid

    def end_session(self, session_id, result, digits_found, seconds):
        self.conn.execute("UPDATE sessions SET ended_at=?, result=?, digits_found=?, seconds=? WHERE id=?",
                          (time.time(), result, digits_found, seconds, session_id))
        self.conn.commit()

    def log_event(self, session_id, source, user, command, accepted, message):
        self.conn.execute(
            "INSERT INTO events (session_id, ts, source, user, command, accepted, message) VALUES (?,?,?,?,?,?,?)",
            (session_id, time.time(), source, user, command, int(accepted), message))
        self.conn.commit()

    def close(self):
        self.conn.close()

    @staticmethod
    def read_recent(path, limit=10):
        conn = sqlite3.connect(str(path))
        try:
            conn.executescript(SCHEMA)
            rows = conn.execute(
                "SELECT s.id, s.result, s.digits_found, s.seconds, "
                "(SELECT COUNT(*) FROM events e WHERE e.session_id = s.id) "
                "FROM sessions s ORDER BY s.id DESC LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()
        return [{"id": r[0], "result": r[1], "digits_found": r[2], "seconds": r[3], "events": r[4]}
                for r in rows]
