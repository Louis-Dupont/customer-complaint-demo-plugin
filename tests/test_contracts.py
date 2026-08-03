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
    "sender_email",
    "subject",
    "received_at",
    "problem_category",
    "problem_summary",
    "consequence",
    "severity",
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
                    "sender_email": "customer-1@example.com",
                    "subject": "Delivery arrived late",
                    "received_at": "2026-01-01",
                    "problem_category": "late_delivery",
                    "problem_summary": "Delivery arrived late",
                    "consequence": "",
                    "severity": "medium",
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
                    "sender_email": "customer-1@example.com",
                    "subject": "Delivery arrived late",
                    "received_at": "2026-01-01",
                    "problem_category": "late_delivery",
                    "problem_summary": "Delivery arrived late",
                    "consequence": "",
                    "severity": "medium",
                },
                {
                    "sender_email": "unknown@example.com",
                    "subject": "Items missing",
                    "received_at": "2026-01-02",
                    "problem_category": "short_delivery",
                    "problem_summary": "Items missing",
                    "consequence": "Emergency purchase",
                    "severity": "high",
                },
            ]
            self.write_csv(complaints, FIELDS, rows)
            self.write_csv(customers, ["customer_id", "contact_email", "venue_type", "delivery_route", "weekly_deliveries"], [
                {"customer_id": "CUST-001", "contact_email": "customer-1@example.com", "venue_type": "hotel", "delivery_route": "East", "weekly_deliveries": "20"}
            ])
            result = subprocess.run(
                [sys.executable, str(script), str(complaints), str(customers), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads((output / "analysis-metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["complaint_message_count"], 2)
            self.assertEqual(metadata["matched_message_count"], 1)
            self.assertEqual(metadata["unmatched_message_count"], 1)
            with (output / "analysis-data.csv").open(encoding="utf-8", newline="") as handle:
                joined = list(csv.DictReader(handle))
            self.assertEqual(list(joined[0]), FIELDS + ["month", "customer_match_status", "customer_id", "customer_venue_type", "customer_delivery_route", "customer_weekly_deliveries"])
            self.assertEqual(joined[0]["customer_match_status"], "matched")
            self.assertEqual(joined[0]["customer_id"], "CUST-001")
            self.assertEqual(joined[1]["customer_match_status"], "unknown_sender_email")
            self.assertEqual(joined[1]["customer_id"], "")
            with (output / "summary-by-category.csv").open(encoding="utf-8", newline="") as handle:
                summaries = {row["problem_category"]: row for row in csv.DictReader(handle)}
            self.assertEqual(summaries["late_delivery"]["unique_customer_count"], "1")
            self.assertEqual(summaries["short_delivery"]["unique_customer_count"], "0")
            self.assertEqual(summaries["short_delivery"]["unmatched_message_count"], "1")


if __name__ == "__main__":
    unittest.main()
