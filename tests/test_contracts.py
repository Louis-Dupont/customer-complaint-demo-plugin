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
            output.mkdir()
            (output / "findings.md").write_text("stale conclusion\n", encoding="utf-8")
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
            self.assertFalse((output / "findings.md").exists())

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

            with (output / "summary-by-category-venue-route.csv").open(encoding="utf-8", newline="") as handle:
                combined = list(csv.DictReader(handle))
            hotel_east = [
                row for row in combined
                if row["problem_category"] == "late_delivery"
                and row["customer_venue_type"] == "hotel"
                and row["customer_delivery_route"] == "East"
            ]
            self.assertEqual(len(hotel_east), 1)
            self.assertEqual(hotel_east[0]["message_count"], "1")
            self.assertEqual(hotel_east[0]["unique_customer_count"], "1")

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

    def test_analysis_skill_is_staged_without_a_hardcoded_demo_finding(self) -> None:
        skill = (SKILLS / "analyze-complaint-patterns" / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILLS / "analyze-complaint-patterns" / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Stage 1 — Inbox Map", skill)
        self.assertIn("Stage 2 — Pattern Deep Dive", skill)
        self.assertIn("stop", skill[skill.index("## Stage 1 — Inbox Map"):skill.index("## Stage 2 — Pattern Deep Dive")])
        self.assertIn("follow-up actions", skill)
        self.assertIn("waiting for the human", skill)
        self.assertNotIn("short_delivery", skill)
        self.assertNotIn("hotel/East", skill)
        self.assertNotIn("hotel customers on the East", skill)
        self.assertIn("wait for my choice", metadata)

    def test_delete_demo_previews_then_deletes_only_marked_project(self) -> None:
        script = SKILLS / "delete-customer-complaint-demo" / "scripts" / "delete_demo.py"
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "Customer Complaint Demo"
            project.mkdir()
            marker = {
                "schema_version": 2,
                "display_name": "Customer Complaint Demo",
                "slug": "customer-complaint-demo",
                "project_directory": str(project),
            }
            (project / ".customer-complaint-demo-project.json").write_text(
                json.dumps(marker), encoding="utf-8"
            )
            (project / "demo-output.txt").write_text("temporary", encoding="utf-8")

            preview = subprocess.run(
                [sys.executable, str(script), "--project-dir", str(project)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue(project.exists())
            self.assertIn("No files were removed", preview.stdout)

            deletion = subprocess.run(
                [sys.executable, str(script), "--project-dir", str(project), "--yes"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(deletion.returncode, 0, deletion.stderr)
            self.assertFalse(project.exists())

    def test_delete_demo_refuses_unmarked_directory(self) -> None:
        script = SKILLS / "delete-customer-complaint-demo" / "scripts" / "delete_demo.py"
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "Customer Complaint Demo"
            project.mkdir()
            result = subprocess.run(
                [sys.executable, str(script), "--project-dir", str(project), "--yes"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(project.exists())
            self.assertIn("refusing to delete", result.stderr)

    def test_demo_can_be_deleted_and_initialized_again(self) -> None:
        initialize = SKILLS / "initialize-customer-complaint-demo" / "scripts" / "initialize.py"
        delete = SKILLS / "delete-customer-complaint-demo" / "scripts" / "delete_demo.py"
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            project = project_root / "Customer Complaint Demo"
            create_command = [
                sys.executable,
                str(initialize),
                "--project-root",
                str(project_root),
                "--no-open",
            ]

            first = subprocess.run(create_command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((project / ".customer-complaint-demo-project.json").is_file())
            self.assertTrue((project / "README.md").is_file())

            removal = subprocess.run(
                [sys.executable, str(delete), "--project-dir", str(project), "--yes"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(removal.returncode, 0, removal.stderr)
            self.assertFalse(project.exists())

            second = subprocess.run(create_command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue((project / ".customer-complaint-demo-project.json").is_file())
            self.assertTrue((project / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()
