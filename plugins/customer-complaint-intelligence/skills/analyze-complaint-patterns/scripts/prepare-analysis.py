#!/usr/bin/env python3
"""Prepare deterministic joined and summary tables for complaint analysis."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


COMPLAINT_FIELDS = [
    "subject",
    "customer_reference",
    "received_at",
    "problem_category",
    "problem_summary",
    "consequence",
    "severity",
]
SEVERITIES = {"low", "medium", "high", "urgent", "unknown"}
CUSTOMER_REFERENCE = re.compile(r"CUST-(?:\d{3}|\?{2})")
KNOWN_CUSTOMER_REFERENCE = re.compile(r"CUST-\d{3}")


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
    if not customers or "customer_id" not in customers[0]:
        raise SystemExit("customers CSV must contain customer_id")
    customer_map: dict[str, dict[str, str]] = {}
    customer_ids: set[str] = set()
    for row in customers:
        customer_id = row["customer_id"].strip()
        if not customer_id:
            raise SystemExit("customers CSV contains a blank customer_id")
        if customer_id in customer_ids:
            raise SystemExit(f"duplicate customer_id: {customer_id}")
        customer_ids.add(customer_id)
        customer_map[customer_id] = row

    joined: list[dict[str, object]] = []
    for row in complaints:
        subject = row["subject"].strip()
        if not subject:
            raise SystemExit("complaints CSV contains a row without subject")
        customer_reference = row["customer_reference"].strip().upper()
        if customer_reference and not CUSTOMER_REFERENCE.fullmatch(customer_reference):
            raise SystemExit(f"invalid customer_reference for {subject!r}")
        try:
            datetime.fromisoformat(row["received_at"].strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise SystemExit(f"invalid complaint row {subject!r}: {exc}") from exc
        if row["severity"].strip().lower() not in SEVERITIES:
            raise SystemExit(f"invalid severity for {subject!r}")
        if not row["problem_category"].strip() or not row["problem_summary"].strip():
            raise SystemExit(f"complaint row {subject!r} needs category and summary")
        customer = customer_map.get(customer_reference) if KNOWN_CUSTOMER_REFERENCE.fullmatch(customer_reference) else None
        output: dict[str, object] = dict(row)
        output["month"] = month(row["received_at"].strip())
        output["customer_match_status"] = (
            "matched"
            if customer
            else "missing_customer_reference"
            if not customer_reference
            else "ambiguous_customer_reference"
            if customer_reference == "CUST-??"
            else "unknown_customer_reference"
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
    # A refreshed Inbox Map has no selected pattern yet. Remove any conclusion
    # left by an earlier deep dive so it cannot appear current.
    (args.output_dir / "findings.md").unlink(missing_ok=True)
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
    combined_rows: list[dict[str, object]] = []
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in joined:
        grouped[(
            str(row.get("problem_category") or "unknown"),
            str(row.get("customer_venue_type") or "unknown"),
            str(row.get("customer_delivery_route") or "unknown"),
        )].append(row)
    for (category, venue, route), group in sorted(grouped.items()):
        combined_rows.append({
            "problem_category": category,
            "customer_venue_type": venue,
            "customer_delivery_route": route,
            "message_count": len(group),
            "unique_customer_count": len({
                str(row["customer_id"])
                for row in group
                if row["customer_id"] and row.get("customer_match_status") == "matched"
            }),
            "unmatched_message_count": sum(
                1 for row in group if row.get("customer_match_status") != "matched"
            ),
            "high_or_urgent_message_count": sum(
                1 for row in group if str(row["severity"]).lower() in {"high", "urgent"}
            ),
        })
    write_csv(
        args.output_dir / "summary-by-category-venue-route.csv",
        combined_rows,
        [
            "problem_category",
            "customer_venue_type",
            "customer_delivery_route",
            "message_count",
            "unique_customer_count",
            "unmatched_message_count",
            "high_or_urgent_message_count",
        ],
    )

    matched = sum(1 for row in joined if row["customer_match_status"] == "matched")
    unmatched = len(joined) - matched
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
