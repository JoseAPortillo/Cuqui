from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives import asymmetric, serialization
from pywebpush import WebPushException, webpush

from cuqui.ports.push_notification import PushNotification

log = logging.getLogger(__name__)

_VAPID_KEYS_FILE = "data/vapid_keys.json"


def _generate_vapid_keys() -> tuple[str, str]:
    private_key = asymmetric.ec.generate_private_key(asymmetric.ec.SECP256R1())
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")

    public_raw = public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )

    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode("utf-8")

    return private_pem, public_b64


def _load_or_generate_keys() -> tuple[str, str | None]:
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    public_key = os.getenv("VAPID_PUBLIC_KEY")

    if private_key and public_key:
        return private_key, public_key

    keys_file = Path(_VAPID_KEYS_FILE)
    if keys_file.exists():
        try:
            data = json.loads(keys_file.read_text())
            return data["private_key"], data["public_key"]
        except (KeyError, json.JSONDecodeError):
            log.warning("Corrupt VAPID keys file, regenerating")

    log.info("Generating new VAPID keys, saving to %s", _VAPID_KEYS_FILE)
    private_pem, public_b64 = _generate_vapid_keys()
    keys_file.parent.mkdir(parents=True, exist_ok=True)
    keys_file.write_text(json.dumps({"private_key": private_pem, "public_key": public_b64}))

    return private_pem, public_b64


class WebPushAdapter:
    def __init__(self) -> None:
        self._private_key, self._public_key = _load_or_generate_keys()
        self._vapid_claims = {"sub": os.getenv("VAPID_CLAIMS_EMAIL", "mailto:cuqui@app.local")}
        self._subscriptions: dict[str, list[dict]] = {}

    def vapid_public_key(self) -> str | None:
        return self._public_key

    def save_subscription(self, session_id: str, subscription: dict) -> None:
        self._subscriptions.setdefault(session_id, []).append(subscription)

    def remove_subscription(self, session_id: str, endpoint: str) -> None:
        subs = self._subscriptions.get(session_id, [])
        self._subscriptions[session_id] = [s for s in subs if s["endpoint"] != endpoint]

    def get_subscriptions(self, session_id: str) -> list[dict]:
        return list(self._subscriptions.get(session_id, []))

    async def send(
        self,
        session_id: str,
        title: str,
        body: str,
        tag: str | None = None,
        data: dict | None = None,
    ) -> None:
        subscriptions = self.get_subscriptions(session_id)
        if not subscriptions:
            return

        payload = json.dumps({
            "title": title,
            "body": body,
            "tag": tag or "cuqui-timer",
            "data": data or {},
        }).encode("utf-8")

        for sub in subscriptions:
            try:
                await asyncio.to_thread(
                    webpush,
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                    },
                    data=payload,
                    vapid_private_key=self._private_key,
                    vapid_claims=self._vapid_claims,
                )
            except WebPushException as exc:
                if exc.response and exc.response.status_code == 410:
                    log.info("Removing expired push subscription: %s", sub["endpoint"])
                    self.remove_subscription(session_id, sub["endpoint"])
                else:
                    log.warning("WebPush send failed for %s: %s", sub["endpoint"], exc)
