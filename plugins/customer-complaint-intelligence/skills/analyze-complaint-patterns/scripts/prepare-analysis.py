#!/usr/bin/env python3
"""Prepare deterministic joined and summary tables for complaint analysis."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from email.utils import parseaddr
from pathlib import Path


COMPLAINT_FIELDS = [
    "sender_email",
    "subject",
    "received_at",
    "problem_category",
    "problem_summary",
    "consequence",
    "severity",
]
SEVERITIES = {"low", "medium", "high", "urgent", "unknown"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("complaints", type=Path)
    parser.add_argument("customers", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def month(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.strftime("%Y-%m")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]], group_field: str) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(group_field) or "unknown")].append(row)
    summaries: list[dict[str, object]] = []
    for key in sorted(grouped):
        group = grouped[key]
        customer_ids = {
            str(row["customer_id"])
            for row in group
            if row["customer_id"] and row.get("customer_match_status") == "matched"
        }
        urgent = sum(1 for row in group if str(row["severity"]).lower() in {"high", "urgent"})
        summaries.append(
            {
                group_field: key,
                "message_count": len(group),
                "unique_customer_count": len(customer_ids),
                "unmatched_message_count": sum(
                    1 for row in group if row.get("customer_match_status") != "matched"
                ),
                "high_or_urgent_message_count": urgent,
            }
        )
    return summaries


def main() -> None:
    args = parse_args()
    complaints = read_csv(args.complaints)
    customers = read_csv(args.customers)
    if not complaints:
        raise SystemExit("complaints CSV has no rows")
    if list(complaints[0]) != COMPLAINT_FIELDS:
        raise SystemExit(f"complaints header must be exactly {COMPLAINT_FIELDS}")
    if not customers or not {"customer_id", "contact_email"} <= set(customers[0]):
        raise SystemExit("customers CSV must contain customer_id and contact_email")
    customer_map: dict[str, dict[str, str]] = {}
    customer_ids: set[str] = set()
    for row in customers:
        customer_id = row["customer_id"].strip()
        contact_email = row["contact_email"].strip().lower()
        if not customer_id:
            raise SystemExit("customers CSV contains a blank customer_id")
        if not contact_email or parseaddr(contact_email)[1] != contact_email or "@" not in contact_email:
            raise SystemExit(f"customers CSV contains an invalid contact_email for {customer_id}")
        if customer_id in customer_ids:
            raise SystemExit(f"duplicate customer_id: {customer_id}")
        if contact_email in customer_map:
            raise SystemExit(f"duplicate contact_email: {contact_email}")
        customer_ids.add(customer_id)
        customer_map[contact_email] = row

    joined: list[dict[str, object]] = []
    for row in complaints:
        sender_email = row["sender_email"].strip().lower()
        subject = row["subject"].strip()
        if not sender_email:
            raise SystemExit("complaints CSV contains a row without sender_email")
        if not subject:
            raise SystemExit("complaints CSV contains a row without subject")
        try:
            datetime.fromisoformat(row["received_at"].strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise SystemExit(f"invalid complaint row from {sender_email!r} / {subject!r}: {exc}") from exc
        if row["severity"].strip().lower() not in SEVERITIES:
            raise SystemExit(f"invalid severity for {sender_email!r} / {subject!r}")
        if not row["problem_category"].strip() or not row["problem_summary"].strip():
            raise SystemExit(f"complaint row {sender_email!r} / {subject!r} needs category and summary")
        customer = customer_map.get(sender_email)
        output: dict[str, object] = dict(row)
        output["month"] = month(row["received_at"].strip())
        output["customer_match_status"] = (
            "matched" if customer else "missing_sender_email" if not sender_email else "unknown_sender_email"
        )
        output["customer_id"] = customer["customer_id"] if customer else ""
        if customer:
            for key, value in customer.items():
                if key in {"customer_id", "contact_email"}:
                    continue
                output[f"customer_{key}"] = value
        else:
            for key in customers[0]:
                if key not in {"customer_id", "contact_email"}:
                    output[f"customer_{key}"] = ""
        joined.append(output)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    joined_fields = COMPLAINT_FIELDS + [
        "month",
        "customer_match_status",
        "customer_id",
    ] + [f"customer_{key}" for key in customers[0] if key not in {"customer_id", "contact_email"}]
    write_csv(args.output_dir / "analysis-data.csv", joined, joined_fields)
    write_csv(args.output_dir / "summary-by-category.csv", summarize(joined, "problem_category"), [
        "problem_category", "message_count", "unique_customer_count", "unmatched_message_count", "high_or_urgent_message_count"
    ])
    write_csv(args.output_dir / "summary-by-venue.csv", summarize(joined, "customer_venue_type"), [
        "customer_venue_type", "message_count", "unique_customer_count", "unmatched_message_count", "high_or_urgent_message_count"
    ])
    write_csv(args.output_dir / "summary-by-route.csv", summarize(joined, "customer_delivery_route"), [
        "customer_delivery_route", "message_count", "unique_customer_count", "unmatched_message_count", "high_or_urgent_message_count"
    ])
    write_csv(args.output_dir / "summary-by-month.csv", summarize(joined, "month"), [
        "month", "message_count", "unique_customer_count", "unmatched_message_count", "high_or_urgent_message_count"
    ])

    matched = sum(1 for row in joined if row["customer_match_status"] == "matched")
    unmatched = len(joined) - matched
    if unmatched > max(5, len(joined) // 4):
        raise SystemExit(
            f"too many complaint messages lack a customer match: {unmatched}/{len(joined)}; resolve the join before analysis"
        )
    metadata = {
        "complaint_message_count": len(joined),
        "customer_population_count": len(customers),
        "matched_message_count": matched,
        "unmatched_message_count": unmatched,
        "unique_complaining_customer_count": len(
            {row["customer_id"] for row in joined if row["customer_match_status"] == "matched"}
        ),
        "period_start": min(row["received_at"] for row in joined),
        "period_end": max(row["received_at"] for row in joined),
    }
    (args.output_dir / "analysis-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
