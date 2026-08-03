---
name: extract-gmail-complaints
description: Turn a defined Gmail population of customer complaint threads into a source-linked CSV with one row per complaint case. In the Customer Complaint Demo, a bare invocation uses the demo's prepared Gmail scope and workspace handoff; elsewhere, ask for missing boundaries. Do not use it to discover patterns, join customer data, investigate findings, or change Gmail.
---

# Extract Gmail Complaints

## Why this skill exists

This skill performs one bounded handoff: it turns unstructured Gmail complaint
threads into a stable, source-linked complaint register that another step can
analyze. It preserves the distinction between messages, threads, and complaint
cases, and keeps uncertainty visible through `extraction_confidence`.

Stop after the validated CSV exists. Do not summarize business patterns, join a
customer file, choose labels, or modify Gmail.

## Contract

### Inputs

- An active Gmail connection to the mailbox the human named.
- An explicit Gmail search scope (for example, a query supplied in the prompt).
  If the scope is ambiguous, ask before searching; never silently scan a
  broader mailbox.
- An output path supplied by the human. If none is supplied, ask once rather
  than scattering a file in an unexpected directory.

### Customer Complaint Demo defaults

When the current working project contains `.customer-complaint-demo-project.json`
with `slug: customer-complaint-demo`, the demo has already defined both missing
boundaries. A bare invocation must use them without asking:

- Gmail query: `label:"Demo/Northstar Complaint Demo" -in:trash`
- output: `workspace/complaints.csv`

State those defaults briefly, then proceed. If the human supplies a different
scope or output path, honor the explicit request. This exception is limited to
the marked demo project; never infer a mailbox scope or output path in a normal
client project.

### Output

Write one UTF-8 CSV at the agreed path with this exact header and column order:

```text
case_id,thread_id,source_url,customer_id,received_at,problem_category,problem_summary,consequence,severity,extraction_confidence
```

One row represents one customer-reported problem (a complaint case), not one
email message. Repeated follow-up messages about the same problem in one
thread remain one row. If a thread contains genuinely separate problems,
create one row per problem and give each row the same `thread_id` and
`source_url`. If the boundary is unclear, keep one case and lower confidence
instead of inventing a split.

Field meanings:

- `case_id`: non-empty identifier unique within the CSV. Derive it
  deterministically from the source thread and issue number (for example,
  `case-<thread_id>-1`); do not use random IDs.
- `thread_id`: the Gmail thread ID for the source evidence.
- `source_url`: a direct Gmail URL for that thread. Preserve a URL returned by
  Gmail; if only the ID is available, use the canonical authenticated Gmail
  thread URL for that ID.
- `customer_id`: an explicit, stable customer identifier found in the message
  or an already-established mailbox mapping. Leave it blank when unavailable;
  never infer or invent one from a name or address.
- `received_at`: date or timestamp of the first message reporting this case,
  normalized to ISO 8601 (`YYYY-MM-DD` or RFC 3339 datetime).
- `problem_category`: a short, normalized category. Derive a small vocabulary
  from the complete population and reuse equivalent category names; do not
  create a unique category from each sentence. Use `other` when the complaint
  is real but no stable category fits.
- `problem_summary`: concise factual description of what the customer reports;
  do not diagnose a cause or add facts absent from the thread.
- `consequence`: the impact the customer reports. Leave blank when no impact
  is stated; do not turn a guess into a consequence.
- `severity`: one of `low`, `medium`, `high`, `urgent`, or `unknown`. Base it
  on the reported impact and urgency, not on a later business interpretation.
- `extraction_confidence`: a numeric value from `0` to `1` describing how
  directly the row is supported by the source and how clear its case boundary
  is. This is extraction confidence, not probability that the complaint is
  true and not business severity.

## Procedure

1. Resolve the scope and output path. In the marked demo project, use the
   defaults above and record them in the response; in any other project, ask
   once when either boundary is missing. Do not silently broaden a scope.
2. Use Gmail's ID-only `gmail_search_email_ids` when available, paging until
   `next_page_token` is empty. Otherwise use `gmail_search_emails` with the
   same pagination rule. Accumulate every unique message ID before reading any
   body; never repeat the first page as a substitute for the next token.
   Search results are message-level: group the returned records by
   `thread_id` before deciding how many cases exist.
3. Read all candidate bodies with `gmail_batch_read_email` in connector-sized
   chunks (up to 100 IDs per call). This is the normal path, not a fallback.
   Preserve the original message ID, thread ID, and source URL. Use
   `gmail_read_email_thread` only once for a thread that genuinely has more
   than one matching message, or when the batch body is missing or leaves the
   case boundary unresolved. Never read every unique thread one at a time.
4. Exclude messages that are clearly not customer complaints when the scope
   also contains unrelated mail. Report the excluded count; do not silently
   imply that the mailbox was entirely complaints. In the marked Customer
   Complaint Demo, the prepared scope is defined to contain 120 synthetic
   complaint cases, including service-change requests; do not exclude any of
   those 120 messages for being a different complaint category.
5. Classify each complaint thread into one or more cases using the row
   semantics above. Keep follow-ups for the same issue together. Normalize the
   category vocabulary only after reviewing the whole population so equivalent
   problems use the same label.
6. Write the exact CSV schema, quoting commas, quotes, and line breaks with a
   standard CSV writer. Do not add extra columns or a second hidden output.
7. Run `scripts/validate-register.py` from this skill directory against the
   CSV. Fix malformed output before reporting success; do not hand-edit the
   CSV to conceal an extraction problem.
8. Report the output path, search scope, number of messages searched, unique
   threads inspected, complaint cases written, excluded messages/threads, and
   rows with confidence below `0.7`. In the marked demo project, stop before
   declaring success if the complete paginated search does not yield exactly
   120 messages or if the register does not contain exactly 120 rows; report
   the discrepancy instead of silently presenting a partial register.

## Failure and stopping rules

- If Gmail is unavailable, stop and explain that the mailbox connection must
  be restored.
- If a matching thread cannot be read, its ID and URL cannot be preserved, or
  pagination is incomplete, stop before declaring the register complete and
  report the unresolved boundary.
- If no complaints match the confirmed scope, write a header-only CSV and
  report that no cases were found.
- Never apply labels, archive, delete, send, or otherwise change Gmail state.
