"""Command routing — match/case dispatch of all 7 intents.

``process_command()`` receives a concrete ``CuquiCommand`` (one of the
7 intent dataclasses), resolves the target timer by name, and delegates
to the corresponding ``TimerManager`` method.

Domain errors (e.g. invalid state transitions) propagate to the caller.
"""

from __future__ import annotations

from cuqui.application.manage_timers import TimerManager
from cuqui.domain.commands import (
    CancelTimerCommand,
    CuquiCommand,
    ExtendTimerCommand,
    PauseTimerCommand,
    ReduceTimerCommand,
    RenameTimerCommand,
    ResumeTimerCommand,
    SetTimerCommand,
)
from cuqui.domain.timer import Timer

__all__ = [
    "process_command",
]


def _resolve_timer_id(
    manager: TimerManager,
    session_id: str,
    name: str | None,
) -> str:
    """Resolve a timer name (or ``"last"`` / ``None``) to a timer ID.

    Raises ``ValueError`` if the session has no timers or the name
    does not match any known timer.
    """
    timer_id = manager.find_timer_id_by_name(session_id, name)
    if timer_id is None:
        timers = manager.get_all_timers(session_id)
        if not timers:
            raise ValueError(f"No timers in session {session_id!r}")
        raise ValueError(f"Timer with name {name!r} not found")
    return timer_id


def process_command(
    manager: TimerManager,
    session_id: str,
    command: CuquiCommand,
) -> Timer | dict[str, Timer] | None:
    """Route *command* by intent to the matching ``TimerManager`` method.

    Parameters
    ----------
    manager:
        The ``TimerManager`` instance (application state).
    session_id:
        Session scope for the operation.
    command:
        One of the 8 ``CuquiCommand`` types.

    Returns
    -------
    Timer | dict[str, Timer] | None
        - ``SET_TIMER`` → the newly created ``Timer``
        - ``CANCEL_TIMER`` → ``None``
        - ``PAUSE`` / ``RESUME`` / ``EXTEND`` / ``REDUCE`` / ``RENAME`` → updated ``Timer``

    Raises
    ------
    ValueError
        If the timer name cannot be resolved or the intent is unrecognised.
    The same errors as the underlying domain ``Timer`` methods
    (e.g. invalid state transitions).
    """
    match command:
        case SetTimerCommand(duration=d, name=n):
            name = n if n is not None else "last"
            timer = manager.add_timer(session_id, name, d)
            return manager.start_timer(session_id, timer.id)

        case CancelTimerCommand(name=n):
            timer_id = _resolve_timer_id(manager, session_id, n)
            manager.remove_timer(session_id, timer_id)
            return None

        case PauseTimerCommand(name=n):
            timer_id = _resolve_timer_id(manager, session_id, n)
            return manager.pause_timer(session_id, timer_id)

        case ResumeTimerCommand(name=n):
            timer_id = _resolve_timer_id(manager, session_id, n)
            return manager.resume_timer(session_id, timer_id)

        case ExtendTimerCommand(duration=d, name=n):
            if n is None:
                timer = manager.add_timer(session_id, "timer", d)
                return manager.start_timer(session_id, timer.id)
            timer_id = manager.find_timer_id_by_name(session_id, n)
            if timer_id is None:
                timer = manager.add_timer(session_id, n, d)
                return manager.start_timer(session_id, timer.id)
            return manager.extend_timer(session_id, timer_id, d)

        case ReduceTimerCommand(duration=d, name=n):
            timer_id = _resolve_timer_id(manager, session_id, n)
            return manager.reduce_timer(session_id, timer_id, d)

        case RenameTimerCommand(name=n, target_name=target):
            # If user specified which timer to rename, resolve by that name.
            # Otherwise fall back to the last timer.
            timer_id = _resolve_timer_id(manager, session_id, target)
            return manager.rename_timer(session_id, timer_id, n)

        case _:
            raise ValueError(f"Unrecognised command type: {type(command).__name__}")
