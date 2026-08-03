#!/usr/bin/env python3
"""Load the local fixtures into the dedicated demo Gmail mailbox.

This is demo scaffolding, not part of the reusable Codex plugin. It inserts
messages through Gmail's API instead of sending mail, and records every
fixture-to-message mapping so the reset command can act only on known demo
messages.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup"
EMAILS = ROOT / "inbox-fixture" / "emails"
HELD_OUT = ROOT / "inbox-fixture" / "held-out"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
STATE_VERSION = 2
EXPECTED_GMAIL_ACCOUNT = "bobby.shan010@gmail.com"
CONTAINER_LABEL_NAME = "Demo/Northstar Complaint Demo"
SYSTEM_SEED_LABELS = ["INBOX", "UNREAD"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument(
        "--credentials",
        type=Path,
        help="Google OAuth client secrets JSON",
    )
    auth.add_argument(
        "--adc",
        action="store_true",
        help="Use Google Application Default Credentials (gcloud auth application-default login)",
    )
    parser.add_argument("--token", type=Path, default=SETUP / "gmail-token.json")
    parser.add_argument("--state", type=Path, default=SETUP / "gmail-fixture-state.json")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=SETUP / "gmail-seed-receipt.json",
        help="Where to write the seed provenance receipt",
    )
    parser.add_argument(
        "--include-held-out",
        action="store_true",
        help="Also load the held-out message for the final demo step",
    )
    return parser.parse_args()


def load_service(credentials_path: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit(
            "Install demo setup dependencies first: pip install google-api-python-client "
            "google-auth-httplib2 google-auth-oauthlib"
        ) from exc

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials is None or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception:
                # Testing-mode OAuth refresh tokens can expire. Fall back to
                # the normal browser flow instead of leaving the operator with
                # an opaque refresh error.
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
                credentials = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials)


def load_service_adc():
    try:
        import google.auth
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit(
            "Install demo setup dependencies first: pip install google-api-python-client "
            "google-auth-httplib2 google-auth-oauthlib"
        ) from exc

    try:
        credentials, _ = google.auth.default(scopes=SCOPES)
    except Exception as exc:
        raise SystemExit(
            "Google ADC credentials are unavailable; run `gcloud auth application-default "
            "login --disable-quota-project --scopes=https://www.googleapis.com/auth/cloud-platform,"
            "https://www.googleapis.com/auth/gmail.modify` first"
        ) from exc
    return build("gmail", "v1", credentials=credentials)


def assert_expected_account(service) -> None:
    """Refuse to touch a mailbox other than the dedicated demo account."""
    profile = service.users().getProfile(userId="me").execute()
    actual = str(profile.get("emailAddress", "")).strip().lower()
    if actual != EXPECTED_GMAIL_ACCOUNT:
        shown = actual or "<unknown>"
        raise SystemExit(
            f"refusing to seed Gmail account {shown}; expected {EXPECTED_GMAIL_ACCOUNT}"
        )


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_message_id(path: Path) -> str:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    value = str(message.get("Message-ID", "")).strip()
    if not value:
        raise SystemExit(f"fixture has no RFC Message-ID header: {path.name}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def initial_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "container_label": {
            "name": CONTAINER_LABEL_NAME,
            "id": "",
            "created_by_demo": False,
        },
        "messages": [],
        "last_seed": None,
        "last_reset": None,
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return initial_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read fixture state {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("messages", []), list):
        raise SystemExit(f"fixture state must be a JSON object with a messages list: {path}")
    # State files from the first scaffold did not have a version or label
    # provenance. They remain readable, but are upgraded as messages are
    # reused and written back below.
    state = initial_state()
    state.update(raw)
    state["version"] = STATE_VERSION
    container = raw.get("container_label")
    if isinstance(container, dict):
        state["container_label"].update(container)
    state["messages"] = list(raw.get("messages", []))
    return state


def list_labels(service) -> list[dict[str, Any]]:
    return service.users().labels().list(userId="me").execute().get("labels", [])


def ensure_container_label(service, state: dict[str, Any]) -> dict[str, Any]:
    current = list_labels(service)
    existing = next((label for label in current if label.get("name") == CONTAINER_LABEL_NAME), None)
    if existing:
        previous = state.get("container_label", {})
        created_by_demo = bool(previous.get("created_by_demo")) and previous.get("id") == existing.get("id")
        label = {
            "name": CONTAINER_LABEL_NAME,
            "id": existing["id"],
            "created_by_demo": created_by_demo,
        }
    else:
        response = (
            service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": CONTAINER_LABEL_NAME,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        label = {
            "name": CONTAINER_LABEL_NAME,
            "id": response["id"],
            "created_by_demo": True,
        }
    state["container_label"] = label
    return label


def fixture_paths(include_held_out: bool) -> list[tuple[Path, str]]:
    paths = [(path, "main") for path in sorted(EMAILS.glob("*.eml"))]
    if include_held_out:
        paths.extend((path, "held-out") for path in sorted(HELD_OUT.glob("*.eml")))
    return paths


def validate_state(state: dict[str, Any], allowed_files: set[str]) -> dict[str, dict[str, Any]]:
    entries = state.get("messages", [])
    if not isinstance(entries, list):
        raise SystemExit("fixture state messages must be a list")
    by_file: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit("fixture state contains a non-object message entry")
        filename = entry.get("fixture_file")
        if not filename or filename not in allowed_files:
            raise SystemExit(f"fixture state contains unknown fixture file: {filename!r}")
        if filename in by_file:
            raise SystemExit(f"fixture state contains duplicate fixture_file: {filename}")
        if not entry.get("message_id"):
            raise SystemExit(f"fixture state entry has no Gmail message_id: {filename}")
        by_file[filename] = entry
    return by_file


def is_not_found(error: Exception) -> bool:
    response = getattr(error, "resp", None)
    return getattr(response, "status", None) == 404


def get_message(service, message_id: str) -> dict[str, Any] | None:
    try:
        return (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["Message-ID"],
            )
            .execute()
        )
    except Exception as error:  # googleapiclient.errors.HttpError is optional here
        if is_not_found(error):
            return None
        raise


def assert_fixture_message_id(
    message: dict[str, Any], message_id: str, fixture_path: Path
) -> None:
    headers = (message.get("payload") or {}).get("headers", [])
    actual = next(
        (
            str(header.get("value", "")).strip()
            for header in headers
            if str(header.get("name", "")).lower() == "message-id"
        ),
        "",
    )
    expected = fixture_message_id(fixture_path)
    if actual != expected:
        shown = actual or "<missing>"
        raise SystemExit(
            f"refusing to reuse Gmail message {message_id} for {fixture_path.name}: "
            f"RFC Message-ID is {shown}, expected {expected}"
        )


def add_demo_labels(service, message_id: str, container_label_id: str) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["INBOX", "UNREAD", container_label_id]},
        )
        .execute()
    )


def parent_entry(path: Path, entries: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if not message.get("In-Reply-To") and not message.get("References"):
        return None
    match = re.fullmatch(r"complaint-(\d+)\.eml", path.name)
    if not match:
        return None
    previous_name = f"complaint-{int(match.group(1)) - 1:03d}.eml"
    return entries.get(previous_name)


def entry_for_insert(path: Path, kind: str, response: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_file": path.name,
        "fixture_sha256": fixture_sha256(path),
        "rfc_message_id": fixture_message_id(path),
        "kind": kind,
        "message_id": response["id"],
        "thread_id": response.get("threadId", ""),
        "status": "active",
        "container_label": {
            "name": label["name"],
            "id": label["id"],
        },
        "seed_system_labels": list(SYSTEM_SEED_LABELS),
    }


def main() -> None:
    args = parse_args()
    use_adc = bool(getattr(args, "adc", False))
    credentials_path = getattr(args, "credentials", None)
    if use_adc and credentials_path:
        raise SystemExit("choose exactly one Gmail auth mode: --adc or --credentials")
    if not use_adc and not credentials_path:
        raise SystemExit("choose a Gmail auth mode: --adc or --credentials PATH")
    if credentials_path and not credentials_path.is_file():
        raise SystemExit(f"credentials file does not exist: {args.credentials}")

    state = load_state(args.state)
    all_paths = {
        path.name: (path, "main") for path in sorted(EMAILS.glob("*.eml"))
    }
    all_paths.update({path.name: (path, "held-out") for path in sorted(HELD_OUT.glob("*.eml"))})
    entries = validate_state(state, set(all_paths))
    paths = fixture_paths(args.include_held_out)
    service = load_service_adc() if use_adc else load_service(credentials_path, args.token)
    assert_expected_account(service)
    container_label = ensure_container_label(service, state)
    # Persist label ownership before the first message call. If the process is
    # interrupted immediately after label creation, reset can still clean up
    # that exact demo-created label safely.
    write_json(args.state, state)

    inserted: list[str] = []
    reused: list[str] = []
    untrashed: list[str] = []
    for path, kind in paths:
        existing = entries.get(path.name)
        expected_hash = fixture_sha256(path)
        if existing and existing.get("fixture_sha256") and existing["fixture_sha256"] != expected_hash:
            raise SystemExit(
                f"fixture changed after it was seeded: {path.name}; reset or regenerate before reseeding"
            )

        if existing:
            message = get_message(service, existing["message_id"])
            if message is None:
                # The recorded message is genuinely gone; remove only this
                # stale provenance entry and insert a fresh one. We never
                # delete another message by search or by fixture filename.
                state["messages"] = [
                    entry for entry in state["messages"] if entry.get("fixture_file") != path.name
                ]
                entries.pop(path.name, None)
                existing = None
            else:
                assert_fixture_message_id(message, existing["message_id"], path)
                if "TRASH" in message.get("labelIds", []):
                    service.users().messages().untrash(userId="me", id=existing["message_id"]).execute()
                    untrashed.append(path.name)
                add_demo_labels(service, existing["message_id"], container_label["id"])
                existing.update(
                    {
                        "fixture_sha256": expected_hash,
                        "rfc_message_id": fixture_message_id(path),
                        "kind": kind,
                        "status": "active",
                        "thread_id": message.get("threadId", existing.get("thread_id", "")),
                        "container_label": {
                            "name": container_label["name"],
                            "id": container_label["id"],
                        },
                        "seed_system_labels": list(SYSTEM_SEED_LABELS),
                    }
                )
                reused.append(path.name)
                continue

        raw = base64.urlsafe_b64encode(path.read_bytes()).decode("ascii")
        message_body: dict[str, Any] = {
            "raw": raw,
            "labelIds": ["INBOX", "UNREAD", container_label["id"]],
        }
        parent = parent_entry(path, entries)
        if parent and parent.get("thread_id"):
            # The fixture already carries In-Reply-To/References headers; the
            # explicit threadId preserves Gmail's existing reply thread too.
            message_body["threadId"] = parent["thread_id"]
        response = (
            service.users()
            .messages()
            .insert(
                userId="me",
                internalDateSource="dateHeader",
                body=message_body,
            )
            .execute()
        )
        entry = entry_for_insert(path, kind, response, container_label)
        state["messages"].append(entry)
        entries[path.name] = entry
        inserted.append(path.name)
        # Persist after each insert so an interrupted load can resume without
        # creating duplicates.
        write_json(args.state, state)

    state["last_seed"] = {
        "timestamp": now(),
        "include_held_out": args.include_held_out,
        "container_label": dict(container_label),
        "inserted_fixture_files": inserted,
        "reused_fixture_files": reused,
        "untrashed_fixture_files": untrashed,
        "message_ids": [entry["message_id"] for entry in state["messages"]],
    }
    write_json(args.state, state)
    write_json(
        args.receipt,
        {
            "operation": "seed",
            "timestamp": state["last_seed"]["timestamp"],
            "include_held_out": args.include_held_out,
            "container_label": dict(container_label),
            "inserted_fixture_files": inserted,
            "reused_fixture_files": reused,
            "untrashed_fixture_files": untrashed,
            "messages": [
                {
                    "fixture_file": entry["fixture_file"],
                    "kind": entry["kind"],
                    "message_id": entry["message_id"],
                    "thread_id": entry.get("thread_id", ""),
                    "fixture_sha256": entry.get("fixture_sha256", ""),
                    "rfc_message_id": entry.get("rfc_message_id", ""),
                }
                for entry in state["messages"]
            ],
        },
    )
    print(
        f"seeded {len(inserted)} new fixture messages, reused {len(reused)}, "
        f"untrashed {len(untrashed)}; state contains {len(state['messages'])} messages"
    )


if __name__ == "__main__":
    main()
