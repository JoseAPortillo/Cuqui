from __future__ import annotations

import typing


class PushNotification(typing.Protocol):
    def vapid_public_key(self) -> str | None:
        ...

    async def send(
        self,
        session_id: str,
        title: str,
        body: str,
        tag: str | None = None,
        data: dict | None = None,
    ) -> None:
        ...
