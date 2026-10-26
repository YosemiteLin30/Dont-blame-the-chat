"""Thread-safe hand-off between the services thread (chat, panel) and the Pygame loop."""
import queue
import threading
import time
from collections import deque

from chat.commands import parse_chat


class GameBridge:
    def __init__(self, per_user_cooldown=3.0):
        self.commands = queue.Queue()        # (source, user, name, arg)
        self.controls = queue.Queue()        # "restart"
        self.per_user_cooldown = per_user_cooldown
        self._last_by_user = {}
        self._lock = threading.Lock()
        self._snapshot = {"phase": "starting"}
        self.log = deque(maxlen=40)

    # -- from chat / panel ------------------------------------------------------
    def submit_text(self, source, user, text):
        """A raw chat line. Returns True if it was queued as a command."""
        parsed = parse_chat(text)
        if parsed is None:
            return False
        return self.submit(source, user, *parsed)

    def submit(self, source, user, name, arg=None):
        now = time.monotonic()
        if source != "panel":
            if now - self._last_by_user.get(user, -1e9) < self.per_user_cooldown:
                return False
            self._last_by_user[user] = now
        self.commands.put((source, user, name, arg))
        return True

    def restart(self):
        self.controls.put("restart")

    # -- game thread ----------------------------------------------------------------
    def drain_commands(self):
        out = []
        while True:
            try:
                out.append(self.commands.get_nowait())
            except queue.Empty:
                return out

    def drain_controls(self):
        out = []
        while True:
            try:
                out.append(self.controls.get_nowait())
            except queue.Empty:
                return out

    def set_snapshot(self, snap):
        with self._lock:
            self._snapshot = snap

    def add_log(self, text, accepted=True):
        with self._lock:
            self.log.appendleft({"t": time.strftime("%H:%M:%S"), "text": text, "ok": accepted})

    # -- panel ------------------------------------------------------------------------
    def state(self):
        with self._lock:
            return dict(self._snapshot, log=list(self.log)[:15])
