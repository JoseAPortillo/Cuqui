"""Tests for Storage protocol and InMemoryTimerStore adapter.

Covers:
- Storage is a structural Protocol
- InMemoryTimerStore implements Storage protocol
- load/save/list_sessions round-trip
- Multiple sessions are isolated
- Unknown session returns empty dict
"""

from __future__ import annotations

import typing

from cuqui.domain.timer import create_timer

# ── Storage Protocol ────────────────────────────────────────────────────────────


class TestStorageProtocol:
    """Storage SHALL be a Protocol with load/save/list_sessions."""

    def test_storage_is_importable(self) -> None:
        """GIVEN the ports module WHEN importing Storage THEN no error."""

    def test_storage_is_protocol(self) -> None:
        """Storage SHALL be a typing.Protocol."""
        from cuqui.ports.storage import Storage

        assert issubclass(Storage, typing.Protocol)

    def test_storage_has_required_methods(self) -> None:
        """Storage SHALL define load, save, and list_sessions."""
        from cuqui.ports.storage import Storage

        assert hasattr(Storage, "load")
        assert hasattr(Storage, "save")
        assert hasattr(Storage, "list_sessions")


# ── InMemoryTimerStore ─────────────────────────────────────────────────────────


class TestInMemoryTimerStore:
    """InMemoryTimerStore SHALL implement Storage with dict backend."""

    def test_store_is_importable(self) -> None:
        """GIVEN the adapter module WHEN importing InMemoryTimerStore THEN no error."""

    def test_load_unknown_session_returns_empty_dict(self) -> None:
        """GIVEN a session_id that has never been stored WHEN load THEN empty dict."""
        from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

        store = InMemoryTimerStore()
        data = store.load("unknown-session")
        assert isinstance(data, dict)
        assert len(data) == 0

    def test_save_and_load_round_trip(self) -> None:
        """GIVEN timers saved for a session WHEN load THEN retrieves same timers."""
        from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

        store = InMemoryTimerStore()
        timer = create_timer(name="Pasta", duration_secs=300)
        session_id = "s1"

        store.save(session_id, {timer.id: timer})
        loaded = store.load(session_id)

        assert timer.id in loaded
        assert loaded[timer.id].name == "Pasta"
        assert loaded[timer.id].duration == 300

    def test_list_sessions_empty_initially(self) -> None:
        """GIVEN a fresh store WHEN list_sessions THEN empty list."""
        from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

        store = InMemoryTimerStore()
        assert store.list_sessions() == []

    def test_list_sessions_after_save(self) -> None:
        """GIVEN data saved for session s1 WHEN list_sessions THEN contains s1."""
        from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

        store = InMemoryTimerStore()
        timer = create_timer(name="Pasta", duration_secs=300)
        store.save("s1", {timer.id: timer})

        sessions = store.list_sessions()
        assert "s1" in sessions

    def test_multiple_sessions_isolated(self) -> None:
        """GIVEN data saved for sessions s1 and s2 WHEN loading each THEN data is separate."""
        from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

        store = InMemoryTimerStore()
        t1 = create_timer(name="Pasta", duration_secs=300)
        t2 = create_timer(name="Rice", duration_secs=600)

        store.save("s1", {t1.id: t1})
        store.save("s2", {t2.id: t2})

        s1_data = store.load("s1")
        s2_data = store.load("s2")

        assert t1.id in s1_data
        assert t2.id not in s1_data  # isolated
        assert t2.id in s2_data

    def test_overwrite_session_data(self) -> None:
        """GIVEN existing session data WHEN save again THEN data is replaced."""
        from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

        store = InMemoryTimerStore()
        t1 = create_timer(name="Pasta", duration_secs=300)
        store.save("s1", {t1.id: t1})

        t2 = create_timer(name="Rice", duration_secs=600)
        store.save("s1", {t2.id: t2})

        loaded = store.load("s1")
        assert t1.id not in loaded  # replaced
        assert t2.id in loaded
