#!/usr/bin/env python3
"""Prepare deterministic joined and summary tables for complaint analysis."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


COMPLAINT_FIELDS = [
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
        confidence = [float(row["extraction_confidence"]) for row in group]
        summaries.append(
            {
                group_field: key,
                "case_count": len(group),
                "unique_customer_count": len(customer_ids),
                "unmatched_case_count": sum(
                    1 for row in group if row.get("customer_match_status") != "matched"
                ),
                "high_or_urgent_case_count": urgent,
                "average_extraction_confidence": round(sum(confidence) / len(confidence), 3),
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
    for row in customers:
        customer_id = row["customer_id"].strip()
        if not customer_id:
            raise SystemExit("customers CSV contains a blank customer_id")
        if customer_id in customer_map:
            raise SystemExit(f"duplicate customer_id: {customer_id}")
        customer_map[customer_id] = row

    joined: list[dict[str, object]] = []
    seen_case_ids: set[str] = set()
    thread_urls: dict[str, str] = {}
    for row in complaints:
        customer_id = row["customer_id"].strip()
        case_id = row["case_id"].strip()
        thread_id = row["thread_id"].strip()
        source_url = row["source_url"].strip()
        if not case_id or not thread_id or not source_url:
            raise SystemExit("complaints CSV contains a row without case/thread/source identity")
        if case_id in seen_case_ids:
            raise SystemExit(f"duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)
        parsed_url = urlparse(source_url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "mail.google.com":
            raise SystemExit(f"invalid Gmail source_url for {case_id}")
        prior_url = thread_urls.setdefault(thread_id, source_url)
        if prior_url != source_url:
            raise SystemExit(f"thread_id maps to multiple source URLs: {thread_id}")
        try:
            datetime.fromisoformat(row["received_at"].strip().replace("Z", "+00:00"))
            confidence = float(row["extraction_confidence"])
        except ValueError as exc:
            raise SystemExit(f"invalid complaint row {row['case_id']!r}: {exc}") from exc
        if not 0 <= confidence <= 1:
            raise SystemExit(f"invalid extraction_confidence for {row['case_id']!r}")
        if row["severity"].strip().lower() not in SEVERITIES:
            raise SystemExit(f"invalid severity for {row['case_id']!r}")
        if not row["problem_category"].strip() or not row["problem_summary"].strip():
            raise SystemExit(f"complaint row {row['case_id']!r} needs category and summary")
        customer = customer_map.get(customer_id)
        output: dict[str, object] = dict(row)
        output["month"] = month(row["received_at"].strip())
        output["customer_match_status"] = (
            "matched" if customer else "missing_customer_id" if not customer_id else "unknown_customer_id"
        )
        if customer:
            for key, value in customer.items():
                if key == "customer_id":
                    continue
                output[f"customer_{key}"] = value
        else:
            for key in customers[0]:
                if key != "customer_id":
                    output[f"customer_{key}"] = ""
        joined.append(output)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    joined_fields = COMPLAINT_FIELDS + [
        "month",
        "customer_match_status",
    ] + [f"customer_{key}" for key in customers[0] if key != "customer_id"]
    write_csv(args.output_dir / "analysis-data.csv", joined, joined_fields)
    write_csv(args.output_dir / "summary-by-category.csv", summarize(joined, "problem_category"), [
        "problem_category", "case_count", "unique_customer_count", "unmatched_case_count", "high_or_urgent_case_count", "average_extraction_confidence"
    ])
    write_csv(args.output_dir / "summary-by-venue.csv", summarize(joined, "customer_venue_type"), [
        "customer_venue_type", "case_count", "unique_customer_count", "unmatched_case_count", "high_or_urgent_case_count", "average_extraction_confidence"
    ])
    write_csv(args.output_dir / "summary-by-route.csv", summarize(joined, "customer_delivery_route"), [
        "customer_delivery_route", "case_count", "unique_customer_count", "unmatched_case_count", "high_or_urgent_case_count", "average_extraction_confidence"
    ])
    write_csv(args.output_dir / "summary-by-month.csv", summarize(joined, "month"), [
        "month", "case_count", "unique_customer_count", "unmatched_case_count", "high_or_urgent_case_count", "average_extraction_confidence"
    ])

    matched = sum(1 for row in joined if row["customer_match_status"] == "matched")
    unmatched = len(joined) - matched
    if unmatched > max(5, len(joined) // 4):
        raise SystemExit(
            f"too many complaint cases lack a customer match: {unmatched}/{len(joined)}; resolve the join before analysis"
        )
    metadata = {
        "complaint_case_count": len(joined),
        "customer_population_count": len(customers),
        "matched_case_count": matched,
        "unmatched_case_count": unmatched,
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
