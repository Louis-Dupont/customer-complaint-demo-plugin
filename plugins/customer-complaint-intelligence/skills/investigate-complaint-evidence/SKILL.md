---
name: investigate-complaint-evidence
description: "Investigate one selected customer-complaint finding or follow-up question by tracing it to the complaint register, analysis artifacts, and Gmail source threads. In the Customer Complaint Demo, a bare invocation uses the defined short-delivery finding; elsewhere, require the human's selected finding. Do not use to build the complaint register, discover broad patterns, apply Gmail labels, or decide the business action."
---

# Investigate complaint evidence

## Purpose

Turn one human-selected finding or question into a source-backed evidence brief. Preserve the distinction between what the analysis shows, what the emails report, and what remains uncertain. Stop at investigation; leave any operational decision and Gmail change to the human and the labels skill.

## Inputs

Use the actual outputs of the earlier steps:

- `workspace/complaints.csv`, with these semantic fields:
  `source_url`, `sender_email`, `received_at`, `problem_category`,
  `problem_summary`, `consequence`, and `severity`.
- `workspace/analysis/analysis-data.csv`, where the analysis step has joined
  each `sender_email` to a derived `customer_id` and customer context.
- The selected finding or question, supplied in the user's message or selected
  from the analysis output.
- `workspace/analysis/findings.md` and
  `workspace/analysis/analysis-data.csv` (or the equivalent paths named by the
  analysis step).
- The connected Gmail mailbox, used to read the source threads referenced by
  `source_url`. Gmail identifiers needed by the connector are resolved at
  read time and are not required in the exported register.

In the marked Customer Complaint Demo project (a current working directory
containing `.customer-complaint-demo-project.json` with
`slug: customer-complaint-demo`), a bare invocation selects the demo finding:

> Investigate the short-delivery pattern among hotel customers on the East
> route. Show the supporting cases, comparable exceptions, and original emails.

Use `workspace/complaints.csv`, `workspace/analysis/findings.md`, and
`workspace/analysis/analysis-data.csv`, and write
`workspace/evidence/short-delivery-east-route.md`. If the human supplies a
different finding or path, honor it. Outside the marked demo project, ask for a
selected finding when it is missing.

If a required field, source identifier, or analysis artifact is missing, say exactly what is missing and stop. Never invent a customer, case, count, link, or email interpretation.

## Procedure

1. Resolve and restate the selected finding as one bounded question. In the
   marked demo project, use the short-delivery finding above when none was
   supplied. Preserve its population,
   comparison, time range, and metric when they are present. If the request is
   ambiguous, ask one focused clarification instead of choosing a materially
   different question.
2. Locate the relevant analysis rows and record the scope and selection rule.
   Use deterministic filtering/counting where possible; do not treat a sentence
   in `findings.md` as sufficient when the underlying rows are available.
3. Build two sets from the actual artifacts:
   - **Supporting messages**: rows that meet the finding's stated condition.
   - **Contradictory or exception messages**: comparable rows that weaken, qualify,
     or fail the apparent pattern.
4. Use each source row as one complaint message; use `source_url` as its trace key
   and deduplicate by `source_url` only when counting the same source twice.
   Count affected customers by the `customer_id` derived in
   `analysis-data.csv`. Keep repeat contacts visible when they explain volume
   or the finding. State which denominator each count uses.
5. Read the relevant Gmail threads with `gmail_read_email_thread`, resolving
   the source URL to the connector's internal message/thread identifier when
   needed. Read the whole thread when follow-ups, corrections, or later
   resolution change the interpretation. Keep source details tied to the
   corresponding `source_url`.
6. Compare the structured row with the source email. Preserve reported wording
   that materially explains the consequence, but summarize rather than copying a
   whole thread. Mark unresolved or conflicting information as unknown.
7. Write the evidence brief to
   `workspace/evidence/<short-finding-slug>.md` (create the directory if needed).
   Also give the human a short direct answer in the conversation. For a voice
   request, lead with the answer, then the strongest evidence, then exceptions or
   the next useful question; do not read the entire report aloud.

## Evidence brief contract

The report must contain these sections, in this order:

1. **Question** — the selected finding or question in the user's language.
2. **Scope and method** — source artifacts, time range, population, metric,
   comparator, and whether counts are messages, cases, or customers.
3. **Answer** — the narrow conclusion supported by the selected evidence.
4. **Supporting messages** — a table with `source_url`, `sender_email`,
   derived `customer_id`, date,
   `problem_category`, concise evidence from the email, and a clickable
   `source_url` for every material case.
5. **Contradictory or exception messages** — the same traceable fields for messages
   that qualify or challenge the finding. Write “none found in the inspected
   scope” only after checking that scope.
6. **What the source emails add** — details that the structured data does not
   capture, such as a concrete consequence, sequence, or customer context.
7. **Open questions** — missing evidence, ambiguous cases, or useful follow-up
   questions; keep these separate from the answer.

Every material number and assertion in the report must be reproducible from the
listed artifacts or linked Gmail threads. Use “reported,” “observed in this
sample,” or “supports the hypothesis” when that is what the evidence means; do
not silently turn a descriptive complaint pattern into a confirmed cause.

## Boundaries

- Do not scan the entire inbox to discover new patterns; broad pattern discovery
  belongs to `analyze-complaint-patterns`.
- Do not rebuild or silently repair `complaints.csv`.
- Do not apply, create, remove, or rename Gmail labels; the human invokes
  `apply-complaint-labels` after deciding what to do.
- Do not send, archive, delete, or modify email.
- Do not select the business priority or prescribe a service change. End with
  evidence and clearly marked open questions so the human can decide.
- If the selected finding cannot be traced to actual rows and source threads,
  report that it is unverified and identify the missing link instead of filling
  the gap with plausible prose.

## Completion

Finish when the evidence brief exists at the agreed path, every material message
has a derived customer identifier when matched and a source link, supporting and exception sets
are explicit, scope and denominators are stated, and the human has received a
concise answer. Do not continue into labeling or end-to-end orchestration.
