from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "customer-complaint-intelligence" / "skills"
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


class ContractTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_register_validator_allows_blank_consequence_and_rejects_bad_shape(self) -> None:
        validator = SKILLS / "extract-gmail-complaints" / "scripts" / "validate-register.py"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "complaints.csv"
            row = {
                field: {
                    "case_id": "case-1",
                    "thread_id": "thread-1",
                    "source_url": "https://mail.google.com/mail/u/0/#inbox/thread-1",
                    "customer_id": "CUST-001",
                    "received_at": "2026-01-01",
                    "problem_category": "late_delivery",
                    "problem_summary": "Delivery arrived late",
                    "consequence": "",
                    "severity": "medium",
                    "extraction_confidence": "0.9",
                }[field]
                for field in FIELDS
            }
            self.write_csv(path, FIELDS, [row])
            result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            with path.open("a", encoding="utf-8") as handle:
                handle.write(",unexpected\n")
            result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_prepare_analysis_preserves_unmatched_customer(self) -> None:
        script = SKILLS / "analyze-complaint-patterns" / "scripts" / "prepare-analysis.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            complaints = root / "complaints.csv"
            customers = root / "customers.csv"
            output = root / "analysis"
            rows = [
                {
                    "case_id": "case-1",
                    "thread_id": "thread-1",
                    "source_url": "https://mail.google.com/mail/u/0/#inbox/thread-1",
                    "customer_id": "CUST-001",
                    "received_at": "2026-01-01",
                    "problem_category": "late_delivery",
                    "problem_summary": "Delivery arrived late",
                    "consequence": "",
                    "severity": "medium",
                    "extraction_confidence": "0.9",
                },
                {
                    "case_id": "case-2",
                    "thread_id": "thread-2",
                    "source_url": "https://mail.google.com/mail/u/0/#inbox/thread-2",
                    "customer_id": "CUST-999",
                    "received_at": "2026-01-02",
                    "problem_category": "short_delivery",
                    "problem_summary": "Items missing",
                    "consequence": "Emergency purchase",
                    "severity": "high",
                    "extraction_confidence": "0.7",
                },
            ]
            self.write_csv(complaints, FIELDS, rows)
            self.write_csv(customers, ["customer_id", "venue_type", "delivery_route", "weekly_deliveries"], [
                {"customer_id": "CUST-001", "venue_type": "hotel", "delivery_route": "East", "weekly_deliveries": "20"}
            ])
            result = subprocess.run(
                [sys.executable, str(script), str(complaints), str(customers), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads((output / "analysis-metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["complaint_case_count"], 2)
            self.assertEqual(metadata["matched_case_count"], 1)
            self.assertEqual(metadata["unmatched_case_count"], 1)
            with (output / "analysis-data.csv").open(encoding="utf-8", newline="") as handle:
                joined = list(csv.DictReader(handle))
            self.assertEqual(joined[0]["customer_match_status"], "matched")
            self.assertEqual(joined[1]["customer_match_status"], "unknown_customer_id")
            with (output / "summary-by-category.csv").open(encoding="utf-8", newline="") as handle:
                summaries = {row["problem_category"]: row for row in csv.DictReader(handle)}
            self.assertEqual(summaries["late_delivery"]["unique_customer_count"], "1")
            self.assertEqual(summaries["short_delivery"]["unique_customer_count"], "0")
            self.assertEqual(summaries["short_delivery"]["unmatched_case_count"], "1")


if __name__ == "__main__":
    unittest.main()
