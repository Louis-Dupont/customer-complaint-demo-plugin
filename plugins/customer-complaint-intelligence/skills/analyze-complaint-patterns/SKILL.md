---
name: analyze-complaint-patterns
description: Analyze an existing source-linked complaint CSV together with a local customer CSV, produce reproducible joined tables, and create a deep interactive visualization of what deserves attention. Use after complaint extraction when the human asks what is happening or which patterns matter. Do not read the inbox, rebuild the register, investigate one finding, or apply Gmail labels.
---

# Analyze Complaint Patterns

This skill exists to turn a validated complaint register and a local customer
table into an explorable analysis. It is the second bounded handoff in the
workflow: the extraction step owns what was reported; this step helps the human
see patterns across cases, customers, time and context.

## Readiness

Require:

- A validated `workspace/complaints.csv` produced by
  `extract-gmail-complaints` (or an equivalent CSV with the exact contract).
- A local `customers.csv` with one row per unique `customer_id`.
- A working project directory in which `workspace/analysis/` can be created.

If either input is missing, malformed, duplicated, or has substantial unmatched
customer IDs, report that before interpreting the results.

## Procedure

1. Confirm the input paths and the period covered. Do not silently choose a
   different mailbox, customer table, or date range.
2. From the plugin skill directory, run
   `python3 scripts/prepare-analysis.py <complaints.csv> <customers.csv> <output_dir>`
   (for the demo: `python3 scripts/prepare-analysis.py
   <demo>/workspace/complaints.csv <demo>/data/customers.csv
   <demo>/workspace/analysis`). This validates the inputs, joins cases to
   customers, preserves unmatched cases, and emits reproducible summary
   tables.
3. Inspect the resulting tables before writing findings. Keep raw email count,
   complaint-case count, and unique-customer count distinct. Preserve repeat
   contacts rather than letting them silently become distinct affected
   customers.
4. Explore useful views of the complete joined population: problem category,
   customer reach, venue or segment, route or other customer dimensions, time,
   service volume, severity, consequence, and extraction confidence. Use
   denominators available in the customer table when they answer a different
   question from raw volume.
5. Write `workspace/analysis/findings.md` with the important patterns, the
   metric and population behind each, the evidence worth investigating, and
   uncertainty or competing explanations. Do not claim that a complaint
   association proves a cause; the goal is a useful fictional business view.
6. Invoke the installed `@visualize` capability directly on
   `workspace/analysis/analysis-data.csv` and the generated summary tables.
   The visualization must allow a human to move from an overview to the cases
   behind a finding. Do not search plugin directories for visualization
   instructions or create a second uncontracted HTML output. If the inline
   visualization surface is unavailable, report that explicitly after leaving
   the tables and `findings.md`; do not claim the analysis step is complete or
   loop trying to discover another visualization mechanism.

## Outputs

The skill must leave these artifacts in `workspace/analysis/`:

- `analysis-data.csv`: one row per complaint case, joined to customer fields
  with a visible `customer_match_status`.
- `summary-by-category.csv`.
- `summary-by-venue.csv`.
- `summary-by-route.csv`.
- `summary-by-month.csv`.
- `analysis-metadata.json`.
- `findings.md`.

Each summary keeps case count, matched unique-customer count, unmatched-case
count, high/urgent case count, and average extraction confidence visible.

- An interactive visualization shown in the Codex conversation through
  `@visualize`. If the human explicitly asks to preserve it, export it to
  `workspace/analysis/complaint-patterns.html`; do not pretend a screenshot is
  the analysis output.

The generated tables are the handoff for `investigate-complaint-evidence`.
Keep the exact `case_id`, `thread_id`, `customer_id`, and `source_url` columns
so every selected result can return to Gmail.

## Boundaries

- Do not search or modify Gmail.
- Do not rebuild or silently repair `complaints.csv`.
- Do not invent customer attributes for unmatched cases.
- Do not deduplicate case rows merely to make a chart look cleaner; make the
  chosen unit explicit in the table or finding.
- Do not choose the business action. End with findings and questions for the
  human to investigate.

## Completion

Finish when the joined population and summary tables pass validation, the
visualization is backed by those actual tables, every material finding names
its unit and population, and `findings.md` exists for the next step. Stop
before source-email investigation or Gmail write-back.
