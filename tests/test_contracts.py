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
    "subject",
    "customer_reference",
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

    def complaint_row(self, *, subject: str, customer_reference: str) -> dict[str, str]:
        return {
            "subject": subject,
            "customer_reference": customer_reference,
            "received_at": "2026-01-01",
            "problem_category": "late_delivery",
            "problem_summary": "Delivery arrived late",
            "consequence": "",
            "severity": "medium",
        }

    def test_register_validator_accepts_supported_references_and_rejects_legacy_header(self) -> None:
        validator = SKILLS / "extract-gmail-complaints" / "scripts" / "validate-register.py"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "complaints.csv"
            rows = [
                self.complaint_row(subject="Known customer", customer_reference="CUST-001"),
                self.complaint_row(subject="Ambiguous customer", customer_reference="CUST-??"),
                self.complaint_row(subject="No reference", customer_reference=""),
            ]
            self.write_csv(path, FIELDS, rows)

            result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            legacy_fields = ["sender_email"] + [field for field in FIELDS if field != "customer_reference"]
            legacy_row = {field: "" for field in legacy_fields}
            legacy_row.update({
                "sender_email": "customer@example.com",
                "subject": "Legacy shape",
                "received_at": "2026-01-01",
                "problem_category": "late_delivery",
                "problem_summary": "Delivery arrived late",
                "consequence": "",
                "severity": "medium",
            })
            self.write_csv(path, legacy_fields, [legacy_row])
            result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("header must be exactly", result.stderr)

    def test_prepare_analysis_joins_by_reference_and_preserves_nonmatches(self) -> None:
        script = SKILLS / "analyze-complaint-patterns" / "scripts" / "prepare-analysis.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            complaints = root / "complaints.csv"
            customers = root / "customers.csv"
            output = root / "analysis"
            rows = [
                self.complaint_row(subject="Known customer", customer_reference="CUST-001"),
                self.complaint_row(subject="Ambiguous customer", customer_reference="CUST-??"),
                self.complaint_row(subject="No reference", customer_reference=""),
                self.complaint_row(subject="Unknown customer", customer_reference="CUST-999"),
            ]
            self.write_csv(complaints, FIELDS, rows)
            self.write_csv(
                customers,
                ["customer_id", "venue_type", "delivery_route"],
                [{"customer_id": "CUST-001", "venue_type": "hotel", "delivery_route": "East"}],
            )

            result = subprocess.run(
                [sys.executable, str(script), str(complaints), str(customers), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            metadata = json.loads((output / "analysis-metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["complaint_message_count"], 4)
            self.assertEqual(metadata["matched_message_count"], 1)
            self.assertEqual(metadata["unmatched_message_count"], 3)

            with (output / "analysis-data.csv").open(encoding="utf-8", newline="") as handle:
                joined = list(csv.DictReader(handle))
            self.assertEqual(
                list(joined[0]),
                FIELDS + [
                    "month",
                    "customer_match_status",
                    "customer_id",
                    "customer_venue_type",
                    "customer_delivery_route",
                ],
            )
            self.assertEqual([row["customer_reference"] for row in joined], ["CUST-001", "CUST-??", "", "CUST-999"])
            self.assertEqual(
                [row["customer_match_status"] for row in joined],
                [
                    "matched",
                    "ambiguous_customer_reference",
                    "missing_customer_reference",
                    "unknown_customer_reference",
                ],
            )
            self.assertEqual([row["customer_id"] for row in joined], ["CUST-001", "", "", ""])

    def test_prepare_analysis_requires_customer_id(self) -> None:
        script = SKILLS / "analyze-complaint-patterns" / "scripts" / "prepare-analysis.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            complaints = root / "complaints.csv"
            customers = root / "customers.csv"
            self.write_csv(complaints, FIELDS, [self.complaint_row(subject="Known customer", customer_reference="CUST-001")])
            self.write_csv(customers, ["venue_type"], [{"venue_type": "hotel"}])

            result = subprocess.run(
                [sys.executable, str(script), str(complaints), str(customers), str(root / "analysis")],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("customers CSV must contain customer_id", result.stderr)


if __name__ == "__main__":
    unittest.main()
