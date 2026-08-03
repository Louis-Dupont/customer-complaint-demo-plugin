#!/usr/bin/env python3
"""Reset only the known demo Gmail fixture messages.

Main fixtures are returned to INBOX and UNREAD. The held-out fixture is moved
to Gmail Trash so a later ``seed_gmail.py --include-held-out`` can untrash and
reuse the same message rather than accumulating copies. No Gmail message is
permanently deleted by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
EXPECTED_GMAIL_ACCOUNT = "bobby.shan010@gmail.com"
CONTAINER_LABEL_NAME = "Demo/Northstar Complaint Demo"
FIXED_ACTION_LABELS = {"Demo/Service Recovery", "Demo/Logistics Investigation"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument("--credentials", type=Path, help="Google OAuth client secrets JSON")
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
        default=SETUP / "gmail-reset-receipt.json",
        help="Where to write the reset provenance receipt",
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
    if not token_path.is_file():
        raise SystemExit(f"Gmail token does not exist; seed the fixture first: {token_path}")
    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            credentials = flow.run_local_server(port=0)
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
            f"refusing to reset Gmail account {shown}; expected {EXPECTED_GMAIL_ACCOUNT}"
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


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"fixture state does not exist; seed the fixture first: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read fixture state {path}: {exc}") from exc
    if not isinstance(state, dict) or not isinstance(state.get("messages"), list):
        raise SystemExit(f"fixture state must be a JSON object with a messages list: {path}")
    return state


def list_labels(service) -> list[dict[str, Any]]:
    return service.users().labels().list(userId="me").execute().get("labels", [])


def action_label_names(state: dict[str, Any]) -> set[str]:
    names = set(FIXED_ACTION_LABELS)
    action_dir = ROOT / "workspace" / "actions"
    if action_dir.is_dir():
        for receipt_path in action_dir.glob("*.json"):
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for key in ("created_label_names", "label_names"):
                values = receipt.get(key, [])
                if isinstance(values, list):
                    names.update(value for value in values if isinstance(value, str) and value.startswith("Demo/"))
    values = state.get("action_label_names", [])
    if isinstance(values, list):
        names.update(value for value in values if isinstance(value, str) and value.startswith("Demo/"))
    return names


def label_by_name(labels: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((label for label in labels if label.get("name") == name), None)


def get_message(service, message_id: str) -> dict[str, Any]:
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
            f"refusing to reset Gmail message {message_id} for {fixture_path.name}: "
            f"RFC Message-ID is {shown}, expected {expected}"
        )


def allowed_fixture_paths() -> dict[str, Path]:
    paths = {path.name: path for path in EMAILS.glob("*.eml")}
    paths.update({path.name: path for path in HELD_OUT.glob("*.eml")})
    return paths


def validate_entries(state: dict[str, Any], paths: dict[str, Path]) -> list[dict[str, Any]]:
    entries = state["messages"]
    names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit("fixture state contains a non-object message entry")
        filename = entry.get("fixture_file")
        if not filename or filename not in paths:
            raise SystemExit(f"fixture state contains unknown fixture file: {filename!r}")
        if filename in names:
            raise SystemExit(f"fixture state contains duplicate fixture_file: {filename}")
        names.add(filename)
        if not entry.get("message_id"):
            raise SystemExit(f"fixture state entry has no Gmail message_id: {filename}")
        expected_hash = entry.get("fixture_sha256")
        if expected_hash and expected_hash != fixture_sha256(paths[filename]):
            raise SystemExit(
                f"fixture changed after it was seeded: {filename}; refuse to reset stale provenance"
            )
    return entries


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
    paths = allowed_fixture_paths()
    entries = validate_entries(state, paths)
    service = load_service_adc() if use_adc else load_service(credentials_path, args.token)
    assert_expected_account(service)
    labels = list_labels(service)

    container_info = state.get("container_label", {})
    container_name = container_info.get("name", CONTAINER_LABEL_NAME)
    container = label_by_name(labels, container_name)
    action_names = action_label_names(state)
    action_labels = [label for name in sorted(action_names) if (label := label_by_name(labels, name))]
    remove_label_ids = [label["id"] for label in action_labels]
    if container:
        remove_label_ids.append(container["id"])

    restored_main: list[dict[str, str]] = []
    trashed_held_out: list[dict[str, str]] = []
    for entry in entries:
        message_id = entry["message_id"]
        filename = entry["fixture_file"]
        kind = entry.get("kind", "held-out" if filename.startswith("heldout") else "main")
        current = get_message(service, message_id)
        assert_fixture_message_id(current, message_id, paths[filename])
        entry["rfc_message_id"] = fixture_message_id(paths[filename])
        body: dict[str, list[str]] = {}
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        if kind == "main":
            if "TRASH" in current.get("labelIds", []):
                service.users().messages().untrash(userId="me", id=message_id).execute()
            body["addLabelIds"] = ["INBOX", "UNREAD"]
            service.users().messages().modify(userId="me", id=message_id, body=body).execute()
            entry["status"] = "active"
            entry["container_label"] = {
                "name": container_name,
                "id": container.get("id", container_info.get("id", "")) if container else container_info.get("id", ""),
            }
            restored_main.append(
                {
                    "fixture_file": filename,
                    "message_id": message_id,
                    "thread_id": entry.get("thread_id", ""),
                    "rfc_message_id": entry.get("rfc_message_id", ""),
                }
            )
        else:
            if body:
                service.users().messages().modify(userId="me", id=message_id, body=body).execute()
            # Trash is reversible; do not call messages.delete here.
            service.users().messages().trash(userId="me", id=message_id).execute()
            entry["status"] = "trashed"
            entry["container_label"] = {
                "name": container_name,
                "id": container.get("id", container_info.get("id", "")) if container else container_info.get("id", ""),
            }
            trashed_held_out.append(
                {
                    "fixture_file": filename,
                    "message_id": message_id,
                    "thread_id": entry.get("thread_id", ""),
                    "rfc_message_id": entry.get("rfc_message_id", ""),
                }
            )

    # Remove labels from the known fixture messages, but keep the label
    # definitions in Gmail. Deleting a user label is global and could affect a
    # message someone added to it after the seed; the demo only owns its exact
    # recorded fixture-message mappings.
    deleted_labels: list[dict[str, str]] = []

    timestamp = now()
    receipt = {
        "operation": "reset",
        "timestamp": timestamp,
        "container_label": {
            "name": container_name,
            "id": container.get("id", container_info.get("id", "")) if container else container_info.get("id", ""),
            "removed_from_fixture_messages": True,
            "deleted": False,
        },
        "action_labels": [
            {
                "name": label.get("name", ""),
                "id": label.get("id", ""),
                "removed_from_fixture_messages": True,
                "deleted": False,
            }
            for label in action_labels
        ],
        "deleted_labels": deleted_labels,
        "restored_main_messages": restored_main,
        "trashed_held_out_messages": trashed_held_out,
    }
    state["last_reset"] = receipt
    # Keep held-out entries with status=trashed. Seed can untrash and reuse the
    # recorded ID, which prevents duplicate copies on repeated rehearsals.
    write_json(args.state, state)
    write_json(args.receipt, receipt)
    print(
        f"restored {len(restored_main)} main fixtures, trashed {len(trashed_held_out)} held-out fixtures, "
        f"removed {len(action_labels)} action labels from known messages"
    )


if __name__ == "__main__":
    main()
