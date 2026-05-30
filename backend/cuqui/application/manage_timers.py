"""TimerManager — session-scoped CRUD and domain state delegation.

Provides a two-level map ``session_id → timer_id → Timer`` and
delegates all state transitions (start, pause, resume, cancel,
complete, extend, reduce, rename) to the domain ``Timer`` methods.

Domain errors (e.g., invalid transitions) propagate to the caller.
"""

from __future__ import annotations

from cuqui.domain.timer import Timer, TimerStatus, create_timer

__all__ = [
    "TimerManager",
]


class TimerManager:
    """Manage ``Timer`` instances scoped by session ID.

    Usage::

        manager = TimerManager()
        timer = manager.add_timer("session-1", "Pasta", 300)
        started = manager.start_timer("session-1", timer.id)
    """

    def __init__(self) -> None:
        self._timers: dict[str, dict[str, Timer]] = {}

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add_timer(self, session_id: str, name: str, duration: int) -> Timer:
        """Create a new pending ``Timer`` and store it in *session_id*.

        Returns the newly created ``Timer`` (it is also stored).
        """
        timer = create_timer(name=name, duration_secs=duration)
        self._timers.setdefault(session_id, {})[timer.id] = timer
        return timer

    def get_timer(self, session_id: str, timer_id: str) -> Timer | None:
        """Return the timer identified by *timer_id* or ``None``."""
        return self._timers.get(session_id, {}).get(timer_id)

    def get_all_timers(self, session_id: str) -> dict[str, Timer]:
        """Return a shallow copy of all timers in *session_id*."""
        return dict(self._timers.get(session_id, {}))

    def remove_timer(self, session_id: str, timer_id: str) -> Timer | None:
        """Remove and return the timer, or ``None`` if it does not exist."""
        return self._timers.get(session_id, {}).pop(timer_id, None)

    # ── State transitions ────────────────────────────────────────────────────

    def start_timer(self, session_id: str, timer_id: str) -> Timer:
        """pending → running.  Delegates to ``Timer.start()``."""
        updated = self._timers[session_id][timer_id].start()
        self._timers[session_id][timer_id] = updated
        return updated

    def pause_timer(self, session_id: str, timer_id: str) -> Timer:
        """running → paused.  Delegates to ``Timer.pause()``."""
        updated = self._timers[session_id][timer_id].pause()
        self._timers[session_id][timer_id] = updated
        return updated

    def resume_timer(self, session_id: str, timer_id: str) -> Timer:
        """paused → running.  Delegates to ``Timer.resume()``."""
        updated = self._timers[session_id][timer_id].resume()
        self._timers[session_id][timer_id] = updated
        return updated

    def cancel_timer(self, session_id: str, timer_id: str) -> Timer:
        """active → cancelled.  Delegates to ``Timer.cancel()``."""
        updated = self._timers[session_id][timer_id].cancel()
        self._timers[session_id][timer_id] = updated
        return updated

    def complete_timer(self, session_id: str, timer_id: str) -> Timer:
        """running → completed.  Delegates to ``Timer.complete()``."""
        updated = self._timers[session_id][timer_id].complete()
        self._timers[session_id][timer_id] = updated
        return updated

    # ── Duration & metadata ──────────────────────────────────────────────────

    def extend_timer(self, session_id: str, timer_id: str, seconds: int) -> Timer:
        """Add *seconds* to remaining time.  Delegates to ``Timer.extend()``."""
        updated = self._timers[session_id][timer_id].extend(seconds)
        self._timers[session_id][timer_id] = updated
        return updated

    def reduce_timer(self, session_id: str, timer_id: str, seconds: int) -> Timer:
        """Subtract *seconds* (clamped at 0).  Delegates to ``Timer.reduce()``."""
        updated = self._timers[session_id][timer_id].reduce(seconds)
        self._timers[session_id][timer_id] = updated
        return updated

    def rename_timer(self, session_id: str, timer_id: str, name: str) -> Timer:
        """Set a new name.  Delegates to ``Timer.rename()``."""
        updated = self._timers[session_id][timer_id].rename(name)
        self._timers[session_id][timer_id] = updated
        return updated

    # ── Countdown tick ────────────────────────────────────────────────────────

    def tick_all(self) -> dict[str, dict[str, Timer]]:
        """Decrement all running timers by 1 second across every session.

        Returns a map of ``session_id → {timer_id → updated_timer}``
        for every timer whose state changed during this tick.
        """
        changed: dict[str, dict[str, Timer]] = {}
        for sid, timers in self._timers.items():
            for tid, timer in timers.items():
                if timer.status != TimerStatus.RUNNING:
                    continue
                new_remaining = timer.remaining - 1
                if new_remaining <= 0:
                    updated = timer.complete()
                else:
                    updated = Timer(
                        id=timer.id,
                        name=timer.name,
                        duration=timer.duration,
                        remaining=new_remaining,
                        status=timer.status,
                        created_at=timer.created_at,
                    )
                self._timers[sid][tid] = updated
                changed.setdefault(sid, {})[tid] = updated
        return changed

    # ── Lookup helpers ───────────────────────────────────────────────────────

    def find_timer_id_by_name(self, session_id: str, name: str) -> str | None:
        """Find a timer ID by its display name.

        If *name* is None or ``"last"``, returns the most recently added
        timer ID for the session.  Returns ``None`` if no timer matches.
        """
        timers = self._timers.get(session_id, {})
        if not timers:
            return None

        if name is None or name == "last":
            # Python 3.7+ dict preserves insertion order — last added wins
            return list(timers.keys())[-1]

        for tid, t in timers.items():
            if t.name == name:
                return tid
        return None
