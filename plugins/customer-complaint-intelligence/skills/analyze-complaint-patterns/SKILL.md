---
name: analyze-complaint-patterns
description: Analyze an existing Gmail-derived complaint CSV together with a local customer CSV, produce reproducible joined tables, and create a deep interactive visualization of what deserves attention. In the Customer Complaint Demo, a bare invocation uses the defined local handoffs; elsewhere, confirm missing paths or scope. Do not read the inbox, rebuild the register, investigate one finding, or apply Gmail labels.
---

# Analyze Complaint Patterns

This skill exists to turn a validated complaint register and a local customer
table into an explorable analysis. It is the second bounded handoff in the
workflow: the extraction step owns what was reported; this step helps the human
see patterns across messages, customers, time and context.

## Readiness

Require:

- A validated `workspace/complaints.csv` produced by
  `extract-gmail-complaints` (or an equivalent CSV with the exact contract).
- A local `customers.csv` with one row per customer and a stable `customer_id`
  field.
- A working project directory in which `workspace/analysis/` can be created.

When the current working project contains `.customer-complaint-demo-project.json`
with `slug: customer-complaint-demo`, use the demo handoff without asking:

- complaints: `workspace/complaints.csv`
- customers: `data/customers.csv`
- output directory: `workspace/analysis`

Use an explicitly supplied path when the human gives one. This default applies
only to the marked demo project. In a normal client project, ask for any
missing path or period boundary instead of guessing.

If either input is missing, malformed, duplicated, or has substantial unmatched
customer references, report that before interpreting the results. In the marked
demo, a structurally valid register is not automatically semantically valid:
before preparation, inspect it once for obvious contradictions between each
subject and its complaint fields. If derived fields appear to have drifted onto
neighboring messages, stop before creating analysis artifacts, show a few exact
examples, and ask for extraction to be rerun. Do not read Gmail or repair the
register in this skill. Outside the controlled demo, a generic or stale subject
alone is not evidence that the body-derived classification is wrong. After any
readiness failure, do not present newly generated tables or findings as current;
mention pre-existing artifacts only when they are present and could be confused
with this invocation.

## Procedure

1. Resolve the input paths and period. In the marked demo project, state the
   three defaults above and derive the period from the register; otherwise ask
   when a boundary is missing. Do not silently choose a different mailbox,
   customer table, or date range.
2. Resolve the directory containing this `SKILL.md` and run the preparation
   script from that exact skill directory—not from the plugin root and not by
   searching the installed package tree. Pass every path as its own quoted
   argument because project paths may contain spaces:
   `python3 scripts/prepare-analysis.py "<complaints.csv>" "<customers.csv>"
   "<output_dir>"`. This is the first step that reads the customer
   table and joins the raw `customer_reference` from each message to
   `customers.customer_id`. It preserves blank, ambiguous, and unmatched
   references rather than forcing a customer match, and emits reproducible
   summary tables.
3. Inspect the resulting tables before writing findings. Keep raw email count,
   complaint-case count, and unique-customer count distinct. Preserve repeat
   contacts rather than letting them silently become distinct affected
   customers. Treat `customer_id` as a derived analysis field, not an input
   extracted from Gmail.
4. Explore useful views of the complete joined population: problem category,
   customer reach, venue or segment, route or other customer dimensions, time,
   service volume, severity, and consequence. Use
   denominators available in the customer table when they answer a different
   question from raw volume.
5. Write `workspace/analysis/findings.md` with the important patterns, the
   metric and population behind each, the evidence worth investigating, and
   uncertainty or competing explanations. Do not claim that a complaint
   association proves a cause; the goal is a useful fictional business view.
   In the marked demo, the connected reveal must be prominent and reproducible:
   show the total `short_delivery` population, then the subset involving hotel
   customers on the East route, its unique matched customers, and the remaining
   short-delivery exceptions. Explain that this segment only becomes visible
   after joining complaint references to the customer table. Keep other useful
   observations secondary to this reveal because it is the handoff to the
   investigation step.
6. Use the installed `visualize:visualize` skill on
   `workspace/analysis/analysis-data.csv` and the generated summary tables.
   This is a skill handoff, not a lookup for a tool named `visualize`: load the
   visualization skill from the session's available skills and apply its
   inline-output contract for this visualization handoff. Do not search
   `ALL_TOOLS` or plugin directories for a visualization mechanism.
   The visualization must allow a human to move from an overview to the cases
   behind a finding. In the marked demo, prefer a focused path—category
   overview, the hotel/East short-delivery subset versus its exceptions, then
   the underlying rows—over a generic dashboard with many unrelated controls.
   Do not create a second uncontracted HTML output. If the visualization skill
   is unavailable, report that explicitly after leaving the tables and
   `findings.md`; do not claim the analysis step is complete or loop trying to
   discover another visualization mechanism.

## Outputs

The skill must leave these artifacts in `workspace/analysis/`:

- `analysis-data.csv`: one row per complaint message, with the original
  `subject`, raw `customer_reference`, and timestamp plus the derived
  `customer_id`, joined customer fields, and a visible `customer_match_status`.
- `summary-by-category.csv`.
- `summary-by-venue.csv`.
- `summary-by-route.csv`.
- `summary-by-month.csv`.
- `summary-by-category-venue-route.csv`.
- `analysis-metadata.json`.
- `findings.md`.

Each summary keeps case count, matched unique-customer count, unmatched-case
count, and high/urgent case count visible.

- An interactive visualization shown in the Codex conversation through the
  `visualize:visualize` skill. If the human explicitly asks to preserve it, export it to
  `workspace/analysis/complaint-patterns.html`; do not pretend a screenshot is
  the analysis output.

The generated tables are the handoff for `investigate-complaint-evidence`.
Keep the exact subject, timestamp, raw customer reference, and complaint fields
plus the derived `customer_id`. A later Gmail step can use those observable
values to re-find a message; connector identifiers and source URLs are not
part of the CSV handoff.

## Boundaries

- Do not search or modify Gmail.
- Do not rebuild or silently repair `complaints.csv`.
- Do not invent customer attributes for unmatched cases.
- Do not deduplicate message rows merely to make a chart look cleaner; make the
  chosen unit explicit in the table or finding.
- Do not choose the business action. End with findings and questions for the
  human to investigate.

## Completion

Finish when the joined population and summary tables pass validation, the
visualization is backed by those actual tables, every material finding names
its unit and population, and `findings.md` exists for the next step. Stop
before source-email investigation or Gmail write-back.
