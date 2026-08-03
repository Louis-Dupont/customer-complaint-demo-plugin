#!/usr/bin/env python3
"""Validate the handoff CSV produced by extract-gmail-complaints."""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlparse


FIELDS = [
    "source_url",
    "sender_email",
    "received_at",
    "problem_category",
    "problem_summary",
    "consequence",
    "severity",
]
SEVERITIES = {"low", "medium", "high", "urgent", "unknown"}


def fail(message: str) -> None:
    raise ValueError(message)


def validate_timestamp(value: str, row_number: int) -> None:
    try:
        if "T" in value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            date.fromisoformat(value)
    except ValueError as exc:
        fail(f"row {row_number}: received_at must be ISO 8601, got {value!r}: {exc}")


def validate(path: Path) -> int:
    if not path.is_file():
        fail(f"CSV does not exist: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            fail(f"header must be exactly {FIELDS!r}; got {reader.fieldnames!r}")

        count = 0
        for row_number, row in enumerate(reader, start=2):
            count += 1
            if None in row or set(row) != set(FIELDS):
                fail(f"row {row_number}: row shape does not match the exact header")
            source_url = row["source_url"].strip()
            sender_email = row["sender_email"].strip()
            category = row["problem_category"].strip()
            summary = row["problem_summary"].strip()
            severity = row["severity"].strip().lower()

            parsed_url = urlparse(source_url)
            if parsed_url.scheme != "https" or parsed_url.netloc != "mail.google.com":
                fail(f"row {row_number}: source_url must be an HTTPS Gmail URL")
            if sender_email:
                parsed_sender = parseaddr(sender_email)[1]
                if parsed_sender != sender_email or "@" not in sender_email:
                    fail(f"row {row_number}: sender_email must be a normalized email address")
            if not category:
                fail(f"row {row_number}: problem_category is required")
            if not summary:
                fail(f"row {row_number}: problem_summary is required")
            if not row["received_at"].strip():
                fail(f"row {row_number}: received_at is required")
            validate_timestamp(row["received_at"].strip(), row_number)
            if severity not in SEVERITIES:
                fail(f"row {row_number}: severity must be one of {sorted(SEVERITIES)!r}")

    return count


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} PATH", file=sys.stderr)
        return 2
    try:
        count = validate(Path(argv[1]))
    except (OSError, ValueError) as exc:
        print(f"invalid complaint register: {exc}", file=sys.stderr)
        return 1
    print(f"valid complaint register: {count} message rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
