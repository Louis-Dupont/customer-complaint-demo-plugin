---
name: analyze-complaint-patterns
description: "Guide a human through a staged analysis of an existing Gmail-derived complaint CSV and local customer CSV. First prepare the complete joined population and show an interactive Inbox Map; then stop at one meaningful analytical choice and continue with a focused Pattern Deep Dive selected by the human. In the Customer Complaint Demo, a bare invocation uses the defined local handoffs. Do not read Gmail, rebuild the register, prescribe a business decision, or collapse the experience into one predetermined finding."
---

# Analyze Complaint Patterns

Turn a complaint register into a guided analytical conversation. The skill has
two useful surfaces—not a sequence of permission screens:

1. **Inbox Map** — orientation and pattern discovery across the complete population.
2. **Pattern Deep Dive** — one human-selected pattern, its affected customers,
   comparison, exceptions, and underlying complaint rows.

Prepare the data once. Let filters and row selection happen inside each visual;
return to Codex only when the human chooses a genuinely new analytical direction.

## Readiness and defaults

Require:

- a structurally valid complaint CSV with the extraction contract;
- a customer CSV with one row per customer and a stable `customer_id`;
- a writable analysis output directory;
- the installed `visualize:visualize` skill.

In a project marked by `.customer-complaint-demo-project.json` with
`slug: customer-complaint-demo`, use these defaults without asking:

- complaints: `workspace/complaints.csv`
- customers: `data/customers.csv`
- analysis: `workspace/analysis`

Outside the marked demo, ask only for a missing path or population boundary.
If an input is malformed, duplicated, or too incomplete for the proposed
comparison, explain the limitation and stop. Do not read Gmail or repair the
register. If an obvious source/field contradiction becomes visible during
analysis, stop rather than building a persuasive visualization from it; do not
add a separate semantic-audit ceremony before ordinary analysis.

## Determine the current stage

- Begin with **Inbox Map** when the human invokes the skill without selecting a
  pattern, or when prepared analysis artifacts do not exist.
- Continue with **Pattern Deep Dive** when the latest human response or an
  inline visualization action identifies a pattern from the Inbox Map.
- If the human asks to refresh after the source files changed, rerun preparation
  and return to Inbox Map. Otherwise reuse the prepared artifacts; do not rerun
  the join merely because the conversation advanced.
- In a fresh task with prepared artifacts but no selected pattern, show the
  Inbox Map again rather than guessing what an earlier human chose.

## Shared preparation

Resolve the directory containing this `SKILL.md` and run once:

```text
python3 scripts/prepare-analysis.py "<complaints.csv>" "<customers.csv>" "<analysis_dir>"
```

Use the resulting `analysis-data.csv`, summary tables, and
`analysis-metadata.json` as the common analytical population for both stages.
Keep complaint messages, unique matched customers, unmatched messages, and
repeat contacts distinct. Treat customer attributes as joined context, not as
facts extracted from Gmail. Use customer-population or service-volume
denominators only when the corresponding source field supports the comparison;
never call a complaint share an incident rate.

## Stage 1 — Inbox Map

Inspect the complete joined population before deciding what deserves attention.
Consider:

- problem mix and customer reach;
- high-impact reports and repeat contacts;
- change over time only when the period is long enough to make it meaningful;
- concentration across available customer dimensions;
- disproportionality relative to the customer population or another legitimate
  denominator;
- combinations that are large, unusually concentrated, recurrent, severe, or
  meaningfully different from the rest.

Do not equate “largest category” with “most important finding.” Do not encode a
demo answer or make every other observation secondary to a predetermined
cohort. Identify a small number of genuine candidates from the actual data and
recommend one, stating briefly why it is the best next analytical question.

Use `visualize:visualize` to show one inline **Inbox Map**, not a generic
dashboard or one page per metric. It should help the human understand the whole
inbox and notice where deeper analysis may pay off. Prefer directly comparable
plots, useful annotations, and local selection over control-heavy panels.

Where the inline host supports follow-up actions, include one primary action
for the recommended pattern and at most one meaningful alternative. The action
must send Codex the selected category/dimensions/comparator and explicitly ask
this skill to continue at Pattern Deep Dive using the existing analysis
artifacts. If inline actions are unavailable, ask the same choice once in
prose. Do not ask permission to reveal filters, counts, or rows already present
in the Inbox Map.

After showing the Inbox Map, explain its main orientation in a short message,
recommend the next direction, ask the human, and stop. Do not write
`findings.md`, open Gmail, or continue into the deep dive in the same turn.

## Stage 2 — Pattern Deep Dive

Use the human-selected pattern as the focus. Preserve its population,
comparison, dimensions, metric, and time boundary. Ask one focused clarification
only if the selection is too ambiguous to reproduce; never replace it with a
more convenient pattern.

Reuse `analysis-data.csv` and the existing summaries. Examine:

- why the selected cohort differs from the relevant comparison;
- complaint messages versus unique affected customers;
- customer reach and any legitimate denominator;
- repeat contacts, reported consequences, and severity;
- customer attributes that genuinely help explain the shape of the cohort;
- comparable exceptions and cases that weaken a simple interpretation;
- the complaint rows behind both the pattern and its exceptions.

Use `visualize:visualize` to show one focused **Pattern Deep Dive**. Combine the
concentration and affected-customer views; do not create a separate visual page
for each. Let the human select customers, supporting rows, and exceptions
inside the visual. Include an action to ask Codex to investigate the selected
pattern in original Gmail messages through `investigate-complaint-evidence`;
do not invoke that skill or read Gmail automatically.

Write `workspace/analysis/findings.md` (or the agreed equivalent) as the compact
handoff for source investigation. It must state:

- the selected question and exact population;
- the metric, comparator, denominator, and units;
- what makes the pattern noteworthy;
- affected customers and repeat contacts;
- supporting rows and meaningful exceptions;
- uncertainty and competing explanations;
- the bounded question to carry into source-email investigation.

Do not turn association into cause or choose the business response.

## Persistent outputs

Shared preparation leaves:

- `analysis-data.csv`
- `summary-by-category.csv`
- `summary-by-venue.csv`
- `summary-by-route.csv`
- `summary-by-month.csv`
- `summary-by-category-venue-route.csv`
- `analysis-metadata.json`

Pattern Deep Dive additionally leaves `findings.md`. Visualizations remain
inline in the Codex conversation unless the human explicitly asks to export
one. Do not create a parallel HTML dashboard in the project.

## Boundaries and stopping rules

- Do not search or modify Gmail.
- Do not rebuild or silently repair `complaints.csv`.
- Do not invent customer attributes or force unmatched references to match.
- Do not deduplicate message rows merely to improve a chart; make the unit clear.
- Do not hardcode the demo's expected pattern into this skill.
- Do not ask the human to approve ordinary presentation interactions.
- Do not continue from Inbox Map to Pattern Deep Dive without the human's
  analytical choice.
- Do not continue from Pattern Deep Dive into source investigation, decision,
  or Gmail write-back without a new human request.

Inbox Map is complete when the full population is visible, a useful next
direction is recommended, and the skill is waiting for the human. Pattern Deep
Dive is complete when the selected pattern, comparison, affected customers,
exceptions, underlying rows, focused visual, and `findings.md` are ready for
source investigation.
