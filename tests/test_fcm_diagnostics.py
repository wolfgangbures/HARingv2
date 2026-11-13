"""Exercise push compatibility without requiring Home Assistant on Windows."""

import ast
import asyncio
from base64 import urlsafe_b64encode
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from http_ece import encrypt
import pytest


@pytest.fixture
def coordinator_module():
    """Load the actual patch and coordinator, excluding HA-only imports."""
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ring"
        / "coordinator.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            if all(alias.name in {"logging", "asyncio"} for alias in node.names):
                nodes.append(node)
        elif isinstance(node, ast.ImportFrom):
            if node.module in {"__future__", "base64", "time"}:
                nodes.append(node)
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "_LOGGER"
                for target in node.targets
            ):
                nodes.append(node)
        elif isinstance(node, ast.FunctionDef):
            if node.name == "_padded_urlsafe_b64decode":
                nodes.append(node)
        elif isinstance(node, ast.Try):
            nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == "RingListenCoordinator":
            nodes.append(node)
    namespace = {
        "__name__": "ring_diagnostics_test",
        "BaseDataUpdateCoordinatorProtocol": object,
        "callback": lambda func: func,
    }
    # Undo global dependency patches between tests.
    import firebase_messaging.fcmpushclient as fcm

    with pytest.MonkeyPatch.context() as patch:
        for name in ("_decrypt_raw_data", "_handle_data_message"):
            patch.setattr(fcm.FcmPushClient, name, fcm.FcmPushClient.__dict__[name])
        patch.setattr(fcm, "urlsafe_b64decode", fcm.urlsafe_b64decode)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
        yield SimpleNamespace(**namespace)


def encode(value):
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


@pytest.fixture
def encrypted_message():
    receiver = ec.generate_private_key(ec.SECP256R1())
    sender = ec.generate_private_key(ec.SECP256R1())
    secret = b"test-auth-secret"
    salt = b"0123456789abcdef"
    payload = b'{"test": "private-payload"}'
    public = sender.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    credentials = {
        "keys": {
            "private": encode(
                receiver.private_bytes(
                    serialization.Encoding.DER,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            ),
            "secret": encode(secret),
        }
    }
    ciphertext = encrypt(
        payload,
        salt=salt,
        private_key=sender,
        dh=receiver.public_key(),
        auth_secret=secret,
        version="aesgcm",
    )
    return credentials, public, encode(salt), ciphertext, payload


@pytest.mark.parametrize("raw_point", [False, True])
def test_decryption_logs_metadata_not_secrets(
    coordinator_module, encrypted_message, caplog, raw_point
):
    credentials, public, salt, ciphertext, payload = encrypted_message
    if raw_point:
        public = public[1:]
    with caplog.at_level(logging.DEBUG, logger="ring_diagnostics_test"):
        result = coordinator_module._patched_decrypt_raw_data(
            credentials, encode(public), salt, ciphertext
        )
    assert result == payload
    assert f"public_key_bytes={len(public)}" in caplog.text
    assert "normalized_key_bytes=65 point_prefix=04" in caplog.text
    assert "FCM payload decrypted successfully" in caplog.text
    for value in (*credentials["keys"].values(), encode(public), payload.decode()):
        assert value not in caplog.text


@pytest.mark.parametrize("invalid_key", ["public", "private"])
def test_invalid_key_traceback_identifies_failure(
    coordinator_module, encrypted_message, caplog, invalid_key
):
    credentials, public, salt, ciphertext, _ = encrypted_message
    if invalid_key == "public":
        public = b"\x04" + bytes(64)
    else:
        credentials["keys"]["private"] = encode(b"not-a-DER-key")

    def handle_message(client, message):
        coordinator_module._patched_decrypt_raw_data(
            credentials, encode(public), salt, ciphertext
        )

    coordinator_module._resilient_handle_data_message.__globals__[
        "_orig_handle_data_message"
    ] = handle_message
    with caplog.at_level(logging.DEBUG, logger="ring_diagnostics_test"):
        coordinator_module._resilient_handle_data_message(None, None)
    assert "FCM message processing failure" in caplog.text
    assert "FCM payload decrypted successfully" not in caplog.text
    if invalid_key == "public":
        assert "from_encoded_point" in caplog.text
    else:
        assert "load_der_private_key" in caplog.text
    for value in credentials["keys"].values():
        assert value not in caplog.text


def test_message_failure_does_not_prevent_next_message(coordinator_module):
    handler = Mock(side_effect=[ValueError("Invalid EC key"), None])
    coordinator_module._resilient_handle_data_message.__globals__[
        "_orig_handle_data_message"
    ] = handler
    coordinator_module._resilient_handle_data_message(None, "bad")
    coordinator_module._resilient_handle_data_message(None, "good")
    assert handler.call_count == 2


def test_health_check_reports_delivered_events(coordinator_module, caplog):
    coordinator = coordinator_module.RingListenCoordinator.__new__(
        coordinator_module.RingListenCoordinator
    )
    coordinator.logger = logging.getLogger("ring_diagnostics_test")
    coordinator._events_received = 0
    coordinator._last_event_received = None
    coordinator._listeners = {"entity": (Mock(), 123)}
    coordinator.event_listener = SimpleNamespace(started=True, subscribed=True)
    coordinator.index_alerts = Mock()
    coordinator._async_update_listeners = Mock()
    with caplog.at_level(logging.DEBUG, logger="ring_diagnostics_test"):
        asyncio.run(coordinator._async_health_check(None))
        assert "events_received=0 last_event_age_seconds=None" in caplog.text
        coordinator._on_event(
            SimpleNamespace(doorbot_id=123, kind="ding", is_update=False)
        )
        asyncio.run(coordinator._async_health_check(None))
    assert coordinator._events_received == 1
    assert "events_received=1" in caplog.text
    assert "started=True subscribed=True" in caplog.text
    coordinator._async_update_listeners.assert_called_once_with(123)
