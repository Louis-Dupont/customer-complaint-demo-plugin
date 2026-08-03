"""Offline checks for the Gmail fixture state machine.

These tests replace Gmail with a small in-memory fake. They deliberately never
load credentials or make network calls; the live-account rehearsal remains a
separate acceptance step.
"""

from __future__ import annotations

import importlib.util
import base64
import json
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    path = ROOT / "setup" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Request:
    def __init__(self, value: Any):
        self.value = value

    def execute(self) -> Any:
        return self.value


class FakeMessages:
    def __init__(self, service: "FakeService"):
        self.service = service
        self.next_id = 1

    def insert(self, userId: str, internalDateSource: str, body: dict[str, Any]) -> Request:
        message_id = f"msg-{self.next_id}"
        self.next_id += 1
        thread_id = body.get("threadId", f"thread-{message_id}")
        raw = base64.urlsafe_b64decode(body["raw"])
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        self.service.messages[message_id] = {
            "id": message_id,
            "threadId": thread_id,
            "labelIds": list(body.get("labelIds", [])),
            "payload": {
                "headers": [
                    {
                        "name": "Message-ID",
                        "value": str(parsed.get("Message-ID", "")).strip(),
                    }
                ]
            },
        }
        return Request({"id": message_id, "threadId": thread_id})

    def get(
        self,
        userId: str,
        id: str,
        format: str,
        metadataHeaders: list[str] | None = None,
    ) -> Request:
        return Request(dict(self.service.messages[id]))

    def modify(self, userId: str, id: str, body: dict[str, list[str]]) -> Request:
        message = self.service.messages[id]
        labels = set(message.get("labelIds", []))
        labels.update(body.get("addLabelIds", []))
        labels.difference_update(body.get("removeLabelIds", []))
        message["labelIds"] = sorted(labels)
        return Request(dict(message))

    def untrash(self, userId: str, id: str) -> Request:
        message = self.service.messages[id]
        message["labelIds"] = [label for label in message.get("labelIds", []) if label != "TRASH"]
        return Request(dict(message))

    def trash(self, userId: str, id: str) -> Request:
        message = self.service.messages[id]
        message["labelIds"] = [
            label for label in message.get("labelIds", []) if label not in {"INBOX", "UNREAD"}
        ]
        if "TRASH" not in message["labelIds"]:
            message["labelIds"].append("TRASH")
        return Request(dict(message))


class FakeLabels:
    def __init__(self, service: "FakeService"):
        self.service = service
        self.next_id = 1

    def list(self, userId: str) -> Request:
        return Request({"labels": [dict(label) for label in self.service.labels.values()]})

    def create(self, userId: str, body: dict[str, str]) -> Request:
        label_id = f"Label_{self.next_id}"
        self.next_id += 1
        label = {"id": label_id, "name": body["name"]}
        self.service.labels[label_id] = label
        return Request(dict(label))

    def delete(self, userId: str, id: str) -> Request:
        self.service.labels.pop(id, None)
        for message in self.service.messages.values():
            message["labelIds"] = [label for label in message.get("labelIds", []) if label != id]
        return Request({})


class FakeUsers:
    def __init__(self, service: "FakeService"):
        self.service = service
        self._messages = FakeMessages(service)
        self._labels = FakeLabels(service)

    def messages(self) -> FakeMessages:
        return self._messages

    def labels(self) -> FakeLabels:
        return self._labels

    def getProfile(self, userId: str) -> Request:
        return Request({"emailAddress": self.service.account})


class FakeService:
    def __init__(self, account: str = "bobby.shan010@gmail.com"):
        self.account = account
        self.messages: dict[str, dict[str, Any]] = {}
        self.labels: dict[str, dict[str, str]] = {}
        self._users = FakeUsers(self)

    def users(self) -> FakeUsers:
        return self._users


class GmailSetupStateTests(unittest.TestCase):
    def test_seed_reset_and_held_out_reuse_are_idempotent(self) -> None:
        seed = load_script("seed_gmail")
        reset = load_script("reset_gmail")
        service = FakeService()

        main_fixture = seed.EMAILS / "complaint-019.eml"
        reply_fixture = seed.EMAILS / "complaint-020.eml"
        held_fixture = seed.HELD_OUT / "heldout-001.eml"
        seed.fixture_paths = lambda include: [
            (main_fixture, "main"),
            (reply_fixture, "main"),
            *(([(held_fixture, "held-out")] if include else [])),
        ]

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            credentials = temp_path / "credentials.json"
            credentials.write_text("{}", encoding="utf-8")
            token = temp_path / "token.json"
            state_path = temp_path / "state.json"
            seed_receipt = temp_path / "seed-receipt.json"
            reset_receipt = temp_path / "reset-receipt.json"
            seed.load_service = lambda credentials_path, token_path: service
            reset.load_service = lambda credentials_path, token_path: service

            seed.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": credentials,
                    "token": token,
                    "state": state_path,
                    "receipt": seed_receipt,
                    "include_held_out": True,
                },
            )()
            seed.main()

            self.assertEqual(len(service.messages), 3)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(len(state["messages"]), 3)
            container_id = state["container_label"]["id"]
            self.assertTrue(all(container_id in message["labelIds"] for message in service.messages.values()))
            main_id = next(
                entry["message_id"] for entry in state["messages"] if entry["kind"] == "main"
            )
            held_id = next(
                entry["message_id"] for entry in state["messages"] if entry["kind"] == "held-out"
            )
            main_thread = next(
                entry["thread_id"]
                for entry in state["messages"]
                if entry["fixture_file"] == main_fixture.name
            )
            reply_thread = next(
                entry["thread_id"]
                for entry in state["messages"]
                if entry["fixture_file"] == reply_fixture.name
            )
            self.assertEqual(main_thread, reply_thread)
            self.assertIn("INBOX", service.messages[main_id]["labelIds"])
            self.assertIn("UNREAD", service.messages[main_id]["labelIds"])

            # Simulate the operational skill adding its two demo labels.
            service.labels["action-1"] = {"id": "action-1", "name": "Demo/Service Recovery"}
            service.labels["action-2"] = {"id": "action-2", "name": "Demo/Logistics Investigation"}
            service.messages[main_id]["labelIds"].extend(["action-1", "action-2"])
            # A previous rehearsal may have moved a main fixture to Trash;
            # reset must restore it as an unread inbox message too.
            service.messages[main_id]["labelIds"] = [
                label for label in service.messages[main_id]["labelIds"] if label != "INBOX"
            ] + ["TRASH"]

            reset.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": credentials,
                    "token": token,
                    "state": state_path,
                    "receipt": reset_receipt,
                },
            )()
            reset.main()

            self.assertIn("INBOX", service.messages[main_id]["labelIds"])
            self.assertIn("UNREAD", service.messages[main_id]["labelIds"])
            self.assertNotIn(container_id, service.messages[main_id]["labelIds"])
            self.assertNotIn("action-1", service.messages[main_id]["labelIds"])
            self.assertEqual(service.messages[held_id]["labelIds"], ["TRASH"])
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                next(entry for entry in state["messages"] if entry["message_id"] == held_id)["status"],
                "trashed",
            )
            self.assertTrue(reset_receipt.is_file())
            self.assertEqual(reset_receipt.read_text(encoding="utf-8").count('"operation": "reset"'), 1)

            # A subsequent include-held-out seed reuses/untrashes the same
            # message ID. It must not insert another copy.
            seed.main()
            self.assertEqual(len(service.messages), 3)
            self.assertIn("INBOX", service.messages[held_id]["labelIds"])
            self.assertIn("UNREAD", service.messages[held_id]["labelIds"])
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                next(entry for entry in state["messages"] if entry["message_id"] == held_id)["status"],
                "active",
            )

    def test_seed_and_reset_refuse_the_wrong_authenticated_account(self) -> None:
        seed = load_script("seed_gmail")
        reset = load_script("reset_gmail")
        service = FakeService("someone-else@example.com")

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            credentials = temp_path / "credentials.json"
            credentials.write_text("{}", encoding="utf-8")
            token = temp_path / "token.json"
            state_path = temp_path / "state.json"
            state_path.write_text(json.dumps({"messages": []}), encoding="utf-8")

            seed.load_service = lambda credentials_path, token_path: service
            seed.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": credentials,
                    "token": token,
                    "state": state_path,
                    "receipt": temp_path / "seed-receipt.json",
                    "include_held_out": False,
                },
            )()
            with self.assertRaisesRegex(SystemExit, "expected bobby.shan010@gmail.com"):
                seed.main()
            self.assertEqual(service.messages, {})
            self.assertEqual(service.labels, {})

            reset.load_service = lambda credentials_path, token_path: service
            reset.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": credentials,
                    "token": token,
                    "state": state_path,
                    "receipt": temp_path / "reset-receipt.json",
                },
            )()
            with self.assertRaisesRegex(SystemExit, "expected bobby.shan010@gmail.com"):
                reset.main()
            self.assertEqual(service.messages, {})
            self.assertEqual(service.labels, {})

    def test_adc_mode_uses_adc_loader_for_seed_and_reset(self) -> None:
        seed = load_script("seed_gmail")
        reset = load_script("reset_gmail")
        service = FakeService()
        fixture = seed.EMAILS / "complaint-019.eml"
        seed.fixture_paths = lambda include: [(fixture, "main")]

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            state_path = temp_path / "state.json"
            seed_receipt = temp_path / "seed-receipt.json"
            reset_receipt = temp_path / "reset-receipt.json"

            seed.load_service_adc = lambda: service
            seed.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": None,
                    "adc": True,
                    "token": temp_path / "unused-token.json",
                    "state": state_path,
                    "receipt": seed_receipt,
                    "include_held_out": False,
                },
            )()
            seed.main()
            self.assertEqual(len(service.messages), 1)

            reset.load_service_adc = lambda: service
            reset.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": None,
                    "adc": True,
                    "token": temp_path / "unused-token.json",
                    "state": state_path,
                    "receipt": reset_receipt,
                },
            )()
            reset.main()
            self.assertIn("INBOX", next(iter(service.messages.values()))["labelIds"])

    def test_seed_and_reset_refuse_replaced_recorded_message_ids(self) -> None:
        seed = load_script("seed_gmail")
        reset = load_script("reset_gmail")
        service = FakeService()
        fixture = seed.EMAILS / "complaint-019.eml"
        seed.fixture_paths = lambda include: [(fixture, "main")]

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            credentials = temp_path / "credentials.json"
            credentials.write_text("{}", encoding="utf-8")
            token = temp_path / "token.json"
            state_path = temp_path / "state.json"
            seed_receipt = temp_path / "seed-receipt.json"
            reset_receipt = temp_path / "reset-receipt.json"

            seed.load_service = lambda credentials_path, token_path: service
            seed.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": credentials,
                    "token": token,
                    "state": state_path,
                    "receipt": seed_receipt,
                    "include_held_out": False,
                },
            )()
            seed.main()
            message_id = next(iter(service.messages))
            labels_before_mismatch = list(service.messages[message_id]["labelIds"])

            service.messages[message_id]["payload"]["headers"][0]["value"] = (
                "<unrelated-message@example.com>"
            )
            with self.assertRaisesRegex(SystemExit, "RFC Message-ID is <unrelated-message@example.com>"):
                seed.main()
            self.assertEqual(service.messages[message_id]["labelIds"], labels_before_mismatch)

            reset.load_service = lambda credentials_path, token_path: service
            reset.parse_args = lambda: type(
                "Args",
                (),
                {
                    "credentials": credentials,
                    "token": token,
                    "state": state_path,
                    "receipt": reset_receipt,
                },
            )()
            with self.assertRaisesRegex(SystemExit, "RFC Message-ID is <unrelated-message@example.com>"):
                reset.main()
            self.assertNotIn("TRASH", service.messages[message_id]["labelIds"])

if __name__ == "__main__":
    unittest.main()
