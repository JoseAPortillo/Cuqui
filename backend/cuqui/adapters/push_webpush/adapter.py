from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives import asymmetric, serialization
from pywebpush import WebPushException, webpush

log = logging.getLogger(__name__)

_VAPID_KEYS_FILE = "data/vapid_keys.json"


def _generate_vapid_keys() -> tuple[str, str]:
    private_key = asymmetric.ec.generate_private_key(asymmetric.ec.SECP256R1())
    public_key = private_key.public_key()

    private_der = private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    private_b64 = base64.urlsafe_b64encode(private_der).rstrip(b"=").decode("utf-8")

    public_raw = public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode("utf-8")

    return private_b64, public_b64


def _validate_keys(private_b64: str) -> bool:
    try:
        padding = 4 - len(private_b64) % 4
        if padding != 4:
            private_b64 += "=" * padding
        der = base64.urlsafe_b64decode(private_b64)
        serialization.load_der_private_key(der, password=None)
        return True
    except Exception:
        return False


def _load_or_generate_keys() -> tuple[str, str | None]:
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    public_key = os.getenv("VAPID_PUBLIC_KEY")

    if private_key and public_key:
        return private_key, public_key

    keys_file = Path(_VAPID_KEYS_FILE)
    if keys_file.exists():
        try:
            data = json.loads(keys_file.read_text())
            if _validate_keys(data["private_key"]):
                return data["private_key"], data["public_key"]
            log.warning("VAPID keys file has invalid format, regenerating")
        except (KeyError, json.JSONDecodeError):
            log.warning("Corrupt VAPID keys file, regenerating")

    log.info("Generating new VAPID keys, saving to %s", _VAPID_KEYS_FILE)
    private_b64, public_b64 = _generate_vapid_keys()
    keys_file.parent.mkdir(parents=True, exist_ok=True)
    keys_file.write_text(json.dumps({"private_key": private_b64, "public_key": public_b64}))

    return private_b64, public_b64


class WebPushAdapter:
    def __init__(self, store: object | None = None) -> None:
        self._private_key, self._public_key = _load_or_generate_keys()
        self._vapid_claims = {"sub": os.getenv("VAPID_CLAIMS_EMAIL", "mailto:cuqui@app.local")}
        self._subscriptions: dict[str, dict[str, dict]] = {}
        self._store = store
        log.info(
            "WebPushAdapter initialized (public key hash: %s..., store: %s)",
            self._public_key[:16] if self._public_key else "NONE",
            "yes" if store else "no",
        )

    def vapid_public_key(self) -> str | None:
        return self._public_key

    def save_subscription(self, session_id: str, subscription: dict) -> None:
        self._subscriptions.setdefault(session_id, {})[subscription["endpoint"]] = subscription
        log.info(
            "Push subscription saved for session=%s endpoint=...%s (total: %d)",
            session_id,
            subscription["endpoint"][-16:],
            len(self._subscriptions[session_id]),
        )
        if self._store is not None:
            self._store.save_push_subscription(
                session_id,
                subscription["endpoint"],
                subscription.get("auth", ""),
                subscription.get("p256dh", ""),
            )

    def remove_subscription(self, session_id: str, endpoint: str) -> None:
        subs = self._subscriptions.get(session_id, {})
        if endpoint in subs:
            del subs[endpoint]
            log.info("Push subscription removed for session=%s", session_id)
        if self._store is not None:
            self._store.remove_push_subscription(session_id, endpoint)

    def get_subscriptions(self, session_id: str) -> list[dict]:
        subs = list(self._subscriptions.get(session_id, {}).values())
        if not subs and self._store is not None:
            subs = self._store.load_push_subscriptions(session_id)
            if subs:
                self._subscriptions[session_id] = {s["endpoint"]: s for s in subs}
        return subs

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
            log.debug("No push subscriptions for session=%s, skipping", session_id)
            return

        payload = json.dumps({
            "title": title,
            "body": body,
            "tag": tag or "cuqui-timer",
            "silent": False,
            "data": data or {},
        }).encode("utf-8")

        log.info(
            "Sending push to session=%s (%d subscription(s))",
            session_id,
            len(subscriptions),
        )

        for sub in subscriptions:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        webpush,
                        subscription_info={
                            "endpoint": sub["endpoint"],
                            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                        },
                        data=payload,
                        vapid_private_key=self._private_key,
                        vapid_claims=self._vapid_claims,
                        timeout=5.0,
                        ttl=86400,
                        headers={"Urgency": "high"},
                    ),
                    timeout=10.0,
                )
                log.debug("Push sent successfully to ...%s", sub["endpoint"][-16:])
            except WebPushException as exc:
                if exc.response and exc.response.status_code == 410:
                    log.info("Removing expired push subscription ...%s", sub["endpoint"][-16:])
                    self.remove_subscription(session_id, sub["endpoint"])
                else:
                    log.warning("Push send failed (WebPush) for ...%s: %s", sub["endpoint"][-16:], exc)
            except Exception as exc:
                log.warning("Push send unexpected error for ...%s: %s", sub["endpoint"][-16:], exc)
