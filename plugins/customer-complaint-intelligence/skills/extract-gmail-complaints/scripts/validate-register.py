#!/usr/bin/env python3
"""Validate the handoff CSV produced by extract-gmail-complaints."""

from __future__ import annotations

import csv
import math
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


FIELDS = [
    "case_id",
    "thread_id",
    "source_url",
    "customer_id",
    "received_at",
    "problem_category",
    "problem_summary",
    "consequence",
    "severity",
    "extraction_confidence",
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

        seen_case_ids: set[str] = set()
        source_urls: dict[str, str] = {}
        count = 0
        for row_number, row in enumerate(reader, start=2):
            count += 1
            if None in row or set(row) != set(FIELDS):
                fail(f"row {row_number}: row shape does not match the exact header")
            case_id = row["case_id"].strip()
            thread_id = row["thread_id"].strip()
            source_url = row["source_url"].strip()
            category = row["problem_category"].strip()
            summary = row["problem_summary"].strip()
            severity = row["severity"].strip().lower()
            confidence_text = row["extraction_confidence"].strip()

            if not case_id:
                fail(f"row {row_number}: case_id is required")
            if case_id in seen_case_ids:
                fail(f"row {row_number}: duplicate case_id {case_id!r}")
            seen_case_ids.add(case_id)
            if not thread_id:
                fail(f"row {row_number}: thread_id is required")
            parsed_url = urlparse(source_url)
            if parsed_url.scheme != "https" or parsed_url.netloc != "mail.google.com":
                fail(f"row {row_number}: source_url must be an HTTPS Gmail URL")
            if not category:
                fail(f"row {row_number}: problem_category is required")
            if not summary:
                fail(f"row {row_number}: problem_summary is required")
            if not row["received_at"].strip():
                fail(f"row {row_number}: received_at is required")
            validate_timestamp(row["received_at"].strip(), row_number)
            if severity not in SEVERITIES:
                fail(f"row {row_number}: severity must be one of {sorted(SEVERITIES)!r}")
            try:
                confidence = float(confidence_text)
            except ValueError as exc:
                fail(f"row {row_number}: extraction_confidence must be numeric: {exc}")
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                fail(f"row {row_number}: extraction_confidence must be between 0 and 1")

            previous_url = source_urls.setdefault(thread_id, source_url)
            if previous_url != source_url:
                fail(f"row {row_number}: one thread_id maps to multiple source URLs")

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
    print(f"valid complaint register: {count} case rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
