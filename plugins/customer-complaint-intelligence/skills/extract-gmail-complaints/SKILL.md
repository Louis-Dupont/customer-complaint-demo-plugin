---
name: extract-gmail-complaints
description: Turn a defined Gmail population of customer complaint messages into a structured CSV with one row per matching message. In the Customer Complaint Demo, a bare invocation uses the demo's prepared Gmail scope and workspace handoff; elsewhere, ask for missing boundaries. Do not use it to discover patterns, join customer data, investigate findings, or change Gmail.
---

# Extract Gmail Complaints

## Why this skill exists

This skill performs one bounded handoff: it turns unstructured Gmail complaint
messages into a stable complaint register that another step can analyze. It
records only what can be extracted from Gmail. A customer reference is copied
from the message body when the message states one; the later analysis step can
map that raw value to local customer data. The subject and timestamp let a later
step re-find the message without pretending that a constructed URL is a source
field; Gmail message and thread identifiers remain connector/runtime details
and are not exported.

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
- category vocabulary: `late_delivery`, `short_delivery`, `damaged_items`,
  `stained_items`, `wrong_quantity`, `billing`, and `service_change`

That vocabulary is already the marked demo's classification contract. Use
these meanings directly; do not redesign a taxonomy or invent a rule engine:

- `late_delivery`: timing, delay, missed slot, or late arrival;
- `short_delivery`: an incomplete delivery or item that is missing/short;
- `damaged_items`: damaged, torn, broken, or unusable items;
- `stained_items`: stained or visibly soiled items;
- `wrong_quantity`: a count or product-mix mismatch without missing stock;
- `billing`: invoice, price, charge, or credit issue;
- `service_change`: request to change, pause, or cancel the service.

State those defaults briefly, then proceed. If the human supplies a different
scope or output path, honor the explicit request. This exception is limited to
the marked demo project; never infer a mailbox scope or output path in a normal
client project.

### Output

Write one UTF-8 CSV at the agreed path with this exact header and column order:

```text
subject,customer_reference,received_at,problem_category,problem_summary,consequence,severity
```

One row represents one matching Gmail message. Repeated follow-up messages
about the same problem remain separate rows. Do not invent a case identifier or
collapse the population to one row per thread.

Do not add any other columns: in particular, no sender email, Gmail thread or
message ID, case ID, confidence, or source URL belongs in this handoff.

Field meanings:

- `subject`: the exact Gmail subject for this message. Preserve it so a later
  step can locate the source again without exporting a connector identifier.
- `customer_reference`: the customer reference explicitly written in the
  message body (for example, `CUST-042` or `CUST-??`). Copy the stated value
  verbatim, apart from surrounding whitespace. Do not invent, repair, or look
  up a value from the sender, signature, subject, or customer table. Leave it
  blank only when the message does not state one.
- `received_at`: date or timestamp of this message, normalized to ISO 8601
  (`YYYY-MM-DD` or RFC 3339 datetime).
- `problem_category`: a short, normalized category. In the marked demo, use the
  defined vocabulary above so every later step receives the same contract. In
  another project, derive a small vocabulary from the complete population and
  reuse equivalent category names; do not create a unique category from each
  sentence. Use `other` when the complaint is real but no stable category fits.
- `problem_summary`: concise factual description of what the customer reports;
  do not diagnose a cause or add facts absent from the thread.
- `consequence`: the impact the customer reports. Leave blank when no impact
  is stated; do not turn a guess into a consequence.
- `severity`: one of `low`, `medium`, `high`, `urgent`, or `unknown`. Base it
  on the reported impact and urgency, not on a later business interpretation.

## Procedure

1. Resolve the scope and output path. In the marked demo project, use the
   defaults above and record them in the response; in any other project, ask
   once when either boundary is missing. Do not silently broaden a scope.
2. Use Gmail's ID-only `gmail_search_email_ids` when available, requesting 20
   results per page and following `next_page_token` until it is empty.
   Otherwise use `gmail_search_emails` with the same pagination rule. Keep each
   returned page as one batch; never manually split or re-transcribe a larger
   result page, and never repeat the first page as a substitute for the next
   token. Track unique message IDs internally so a repeated result cannot
   become a duplicate row. If a token resolves to an empty page, treat the
   search as complete and do not call the batch reader with an empty ID list.
   Search results are already the row population:
   retain every matching message. You may group them by thread internally only
   to decide whether a selective thread read is needed; do not export that
   internal identifier. Use the named Gmail operations directly; do not dump or
   search the full tool catalog unless one of them is genuinely unavailable.
3. Read each non-empty result page with `gmail_batch_read_email`. This is the
   normal path, not a fallback: larger batches can exceed Gmail's per-user
   concurrency limit. If a batch returns rate-limited items, retry only those
   failed IDs once in batches of 10; do not reread successful items. In the
   marked demo, continue the search/read page sequence until `next_page_token`
   is empty. Do not pause after an early page to design classification rules or
   implementation code; finish retrieving the bounded population first.
   Preserve the original message/thread identifiers internally and retain the
   subject and timestamp in each output row. If the body states a customer
   reference, preserve it verbatim in the row, including `CUST-??`. Use
   `gmail_read_email_thread` only once for a thread that genuinely has more
   than one matching message, or when the batch body is missing or leaves the
   case boundary unresolved. Retain the first result page exactly like every
   later page; never reconstruct or special-case it manually. Never read every
   unique thread one at a time. Finish retrieving the complete bounded
   population before classification. Then inspect one retained page at a time,
   surface it once if the connector wrapper kept it outside model-visible
   output, and immediately build its keyed row objects. Do not surface or
   classify that page again after those complete keyed rows exist; a page is
   complete only when it is annotated, not merely when its bodies were read.
4. Exclude messages that are clearly not customer complaints when the scope
   also contains unrelated mail. Report the excluded count; do not silently
   imply that the mailbox was entirely complaints. In the marked Customer
   Complaint Demo, the prepared scope is defined to contain 120 synthetic
   complaint messages, including service-change requests; do not exclude any of
   those 120 messages for being a different complaint category.
5. Classify each matching message using the row semantics above. Outside the
   marked demo, normalize the category vocabulary only after reviewing the
   whole population so equivalent problems use the same label. In the marked
   demo, the vocabulary and meanings are already fixed: classify the retrieved
   population, preserve concise message-derived summaries and consequences,
   write the CSV, and validate it without another taxonomy-design pass.
   Use direct semantic classification by the model. Do not build a custom
   regex classifier, rules engine, or extraction script for the synthetic demo;
   the bundled register validator is the only script this step needs to run.
   Work one retrieved page at a time and keep every derived field attached to
   its source message through the Gmail message ID as an internal join key.
   Build complete row objects, not separate positional arrays for categories,
   consequences, severities, or other annotations. Copy subject, timestamp,
   and body-stated reference from that same source object; never retype those
   fields from memory. The internal ID is only an assembly guard and must not
   appear in the CSV. Before combining pages, require the source-ID set and
   annotated-row-ID set to match exactly. While emitting each row, reject an
   obvious contradiction between its source message and derived fields; do not
   add a second full rewrite or stylistic-polish pass. Concise wording may repeat
   when messages report the same thing. In the marked demo, Gmail is the
   extraction source; do not consult the local fixture manifest or `.eml` files
   as an answer key.
6. Write the exact CSV schema, quoting commas, quotes, and line breaks with a
   standard CSV writer. Do not add extra columns or a second hidden output.
7. Run `scripts/validate-register.py` from this skill directory against the
   CSV. This proves the handoff's structure and field constraints, not the
   semantic accuracy of the classifications; the source-paired review in the
   previous step owns that check. Fix malformed output before reporting
   success; do not hand-edit the CSV to conceal an extraction problem.
8. Report the output path, search scope, number of messages searched, unique
   threads inspected, complaint messages written, and excluded messages/threads.
   In the marked demo project, stop before declaring success if the complete paginated search does not yield exactly
   120 messages, if the register does not contain exactly 120 rows, or if any
   row is missing `subject`; report the discrepancy instead of silently
   presenting a partial register.

For the marked demo, the normal execution shape is the bounded paginated
search, six page-sized body reads, one keyed row-assembly pass per page, and one
structural validator run. Do not add exploratory fixture inspection, classifier
implementation, or repeated body dumps to that path.

## Failure and stopping rules

- If Gmail is unavailable, stop and explain that the mailbox connection must
  be restored.
- If a matching message cannot be read, its subject or timestamp cannot
  be preserved, or
  pagination is incomplete, stop before declaring the register complete and
  report the unresolved boundary.
- If no complaints match the confirmed scope, write a header-only CSV and
  report that no cases were found.
- Never apply labels, archive, delete, send, or otherwise change Gmail state.
