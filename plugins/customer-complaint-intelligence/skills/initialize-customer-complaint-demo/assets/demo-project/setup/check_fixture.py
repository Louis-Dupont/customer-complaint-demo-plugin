#!/usr/bin/env python3
"""Check the fictional client fixture before loading it into Gmail."""

from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    customers_path = ROOT / "data" / "customers.csv"
    email_dir = ROOT / "inbox-fixture" / "emails"
    with customers_path.open(encoding="utf-8", newline="") as handle:
        customers = list(csv.DictReader(handle))
    assert len(customers) == 180, len(customers)
    customer_ids = [row["customer_id"] for row in customers]
    assert len(set(customer_ids)) == len(customer_ids)
    assert all(row["customer_name"] and row["weekly_deliveries"] for row in customers)

    manifest_path = ROOT / "setup" / "fixture-manifest.csv"
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    assert len(manifest) == 120
    assert len({row["case_id"] for row in manifest}) == 120
    assert {row["customer_id"] for row in manifest} <= set(customer_ids)
    assert {row["category"] for row in manifest} == {
        "late_delivery",
        "short_delivery",
        "damaged_items",
        "stained_items",
        "wrong_quantity",
        "billing",
        "service_change",
    }

    paths = sorted(email_dir.glob("*.eml"))
    assert len(paths) == 120, len(paths)
    message_ids: list[str] = []
    subjects: list[str] = []
    bodies: list[str] = []
    explicit_references = 0
    replies = 0
    multi_issue = 0
    for path in paths:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        assert message["From"] and message["To"] and message["Date"] and message["Message-ID"]
        message_ids.append(str(message["Message-ID"]))
        subjects.append(str(message["Subject"]))
        body = message.get_body(preferencelist=("plain",)).get_content().strip()
        bodies.append(body)
        explicit_references += bool(re.search(r"Customer reference: CUST-\d{3}\b", body))
        replies += bool(message["In-Reply-To"])
        multi_issue += "quality marks" in body
    assert len(set(message_ids)) == len(message_ids)
    assert len(set(subjects)) >= 30
    assert len(set(bodies)) >= 100
    assert 100 <= explicit_references < len(paths), explicit_references
    assert replies >= 5, replies
    assert multi_issue >= 4, multi_issue
    assert {row["fixture_file"] for row in manifest} == {path.name for path in paths}
    assert {row["message_id"] for row in manifest} == set(message_ids)
    customer_map = {row["customer_id"]: row for row in customers}
    routes = {customer_map[row["customer_id"]]["delivery_route"] for row in manifest}
    assert len(routes) >= 4, routes

    target_cases = []
    target_cases_without_reference = []
    unknown_reference_cases = []
    for row in manifest:
        message = BytesParser(policy=policy.default).parsebytes(
            (email_dir / row["fixture_file"]).read_bytes()
        )
        received = parsedate_to_datetime(str(message["Date"])).date()
        customer = customer_map[row["customer_id"]]
        body = message.get_body(preferencelist=("plain",)).get_content()
        has_explicit_reference = bool(re.search(r"Customer reference: CUST-\d{3}\b", body))
        if "Customer reference: CUST-??" in body:
            unknown_reference_cases.append(row["case_id"])
        if (
            date(2026, 4, 1) <= received <= date(2026, 7, 2)
            and customer["venue_type"] == "hotel"
            and customer["delivery_route"] == "East"
            and row["category"] == "short_delivery"
        ):
            target_cases.append(row["case_id"])
            if not has_explicit_reference:
                target_cases_without_reference.append(row["case_id"])
    assert len(target_cases) == 23, len(target_cases)
    assert not target_cases_without_reference, target_cases_without_reference
    assert len(unknown_reference_cases) >= 4, unknown_reference_cases
    assert not set(target_cases).intersection(unknown_reference_cases)

    held_out = sorted((ROOT / "inbox-fixture" / "held-out").glob("*.eml"))
    assert len(held_out) == 1, len(held_out)
    held_message = BytesParser(policy=policy.default).parsebytes(held_out[0].read_bytes())
    assert held_message["From"] and held_message["To"] and held_message["Date"] and held_message["Message-ID"]
    assert "Customer reference:" in held_message.get_body(preferencelist=("plain",)).get_content()
    assert str(held_message["Date"]).startswith("Tue, 28 Jul 2026")
    assert "Customer reference: CUST-003" in held_message.get_body(preferencelist=("plain",)).get_content()

    print(f"fixture valid: {len(customers)} customers, {len(paths)} main emails, {len(held_out)} held-out email")
    print("subjects:", Counter(subjects).most_common(3))
    print(f"decision cohort: {len(target_cases)} hotel/East short-delivery cases")


if __name__ == "__main__":
    main()
