# Northstar Linen Services demo runbook

This runbook is for the person presenting the demo. The plugin and the
fictional client environment are separate deliverables.

## Starting state

- Open the demo folder as the current Codex project (or start Codex from this
  directory) so relative paths resolve to this folder.
- The `customer-complaint-intelligence` plugin is installed from GitHub.
- The dedicated Gmail account is connected through the Gmail plugin.
- Bobby's mailbox already contains the 120 synthetic Northstar complaint
  messages under the demo-only container label `Demo/Northstar Complaint Demo`.
  The messages are also in the Inbox; the container label is scaffolding
  provenance, not part of the customer story.
- `data/customers.csv` is available locally.
- `workspace/` is empty.

The prepared mailbox is the starting state. Verify it with the Gmail plugin
using `label:"Demo/Northstar Complaint Demo" -in:trash` (it should return 120
main messages). Verify the local fictional data with:

```sh
python3 setup/generate_demo_data.py
python3 setup/check_fixture.py
python3 setup/reset_demo.py
```

Do not run the API seeder for the normal presentation. It is optional
developer scaffolding for rebuilding a mailbox with separately managed Gmail
API credentials; the demo itself needs only the connected Gmail plugin.

## Story

Northstar rents and delivers linen to hotels, restaurants and spas. The support
team receives many complaints but cannot easily see what deserves attention.

The expected analytical movement is:

1. Late delivery is the largest visible source of email.
2. Looking at distinct cases and customer context changes the picture.
3. Short-delivery complaints are a smaller issue concentrated among hotels
   using the East route.
4. Those customers describe rooms or service spaces being left unavailable and
   emergency replacement purchases.
5. The evidence supports investigating that route and routing high-impact cases
   to service recovery, while leaving ordinary delivery complaints in routine
   support.

The point is not the fictional answer. The point is that Codex helps a human
move from a messy inbox to a useful business understanding and then act on it.

## Suggested sequence

Typical waiting times on the demo machine are approximately: extraction two to
six minutes, analysis one to three minutes, investigation under one minute,
and label preview/write-back under thirty seconds. The operator should narrate
the human question while a step is running rather than implying that the work
was instantaneous.

### 1. Extract

Invoke the extraction skill. In this marked demo project, a bare skill
invocation already means the prepared demo scope and
`workspace/complaints.csv`; you can also use this explicit prompt:

> Search Gmail for `label:"Demo/Northstar Complaint Demo" -in:trash`, then turn those Northstar customer complaint emails into a structured CSV at `workspace/complaints.csv`. Keep one row per matching email, preserve the sender, subject, and timestamp, and leave missing fields blank.

Show `workspace/complaints.csv` and one or two source messages. Do not spend the
whole demo reviewing the taxonomy.

### 2. Analyze

Invoke the analysis skill. It uses the extracted register, `data/customers.csv`,
and `workspace/analysis/` automatically in this project; you can also use this
explicit prompt:

> Combine `workspace/complaints.csv` with `data/customers.csv`. Help me understand what deserves attention, and create an interactive visualization.

This is the first step that joins the extracted sender email to the local
customer table; extraction itself does not consult that table.

Start with the obvious volume view, then ask:

> What changes if we look at distinct customers, venue type, route, service
> plan, and delivery volume rather than raw email count?

Use `@visualize` for the deep analysis moment.

### 3. Investigate

Invoke the investigation skill or use normal conversation/voice. A bare skill
invocation uses the demo's short-delivery East-route finding; you can also ask:

> Investigate the short-delivery pattern. Show the customers and original emails that support it, plus counterexamples.

Open two source emails and the evidence brief. Keep the human distinction clear:
the evidence supports an investigation and a handling decision; it does not
pretend to prove a cause.

### 4. Decide and apply

State the human decision:

> For the current Northstar register, label every case where the customer is a hotel on the East route and the complaint category is short delivery. Apply both `Demo/Service Recovery` and `Demo/Logistics Investigation`. Leave ordinary late-delivery complaints in routine support.

Then invoke the label skill. A bare invocation prepares the demo's proposed
labels and exact target rule; it still stops for your approval before changing
Gmail. You can also use this explicit prompt:

> Preview the Gmail labels `Demo/Service Recovery` and `Demo/Logistics Investigation` and the matching threads for that decision.

The deterministic fixture contains 23 expected matches for this rule. Treat a
different count as a prompt to inspect the extracted register before approving.
Review the preview, approve it, and show the operation receipt in
`workspace/actions/`.

### 5. Reuse

For the reuse step, ask the Gmail-connected Codex task to send only
`inbox-fixture/held-out/heldout-001.eml` to Bobby's dedicated mailbox with the
subject prefix `[HELD-OUT]`. This avoids creating a bounce for the fictional
`.example` support address. The prepared rehearsal used exactly one held-out
message with customer reference `CUST-003`.

Then ask:

> Search only the held-out Northstar message (the one with the held-out subject or fixture label) and extract it to `workspace/complaints-heldout.csv`. Process it using the understanding we just developed and show me how it should be handled.

Use the label skill with the held-out sender, subject, and timestamp after the human approves the
same two labels. This demonstrates reuse without rerunning the original
120-message analysis.

The human still triggers the task. Nothing runs automatically in the
background.

## Reset

For a local rehearsal, first use the Gmail plugin to remove both action labels
from the exact demo messages and move the `[HELD-OUT]` message to Trash. Then
run this command from the demo folder:

```sh
python3 setup/reset_demo.py
```

The local reset removes generated workspace files. The prepared Gmail mailbox
is already isolated to Bobby's account and the demo label; if a rehearsal has
changed it, restore the starting state before handing it to the next presenter:
120 main messages in `Demo/Northstar Complaint Demo`, no action labels on those
messages, and the held-out message in Trash. Delivery-failure notices, if any,
should also remain in Trash.

The seed and reset commands leave ignored provenance receipts in `setup/` so a
rehearsal can show exactly which fixture files, Gmail message IDs, thread IDs
and labels were touched. The label definitions remain in Gmail; the reset only
removes those labels from the recorded fixture messages.

## Recovery

- If extraction finds nothing, confirm the Gmail plugin is connected and use
  the exact `label:"Demo/Northstar Complaint Demo" -in:trash` search query.
- If a skill cannot find `workspace/complaints.csv`, confirm Codex is running
  with this demo folder as its project and rerun the preceding step.
- If analysis takes time, let the complete population finish; the analysis
  step may take a few minutes before the visualization appears.
- If visualization fails, keep the generated CSV summaries, start a fresh
  Codex task, and ask to visualize `workspace/analysis/analysis-data.csv`.
- If label preview and approval differ, do not approve; rerun the label skill
  from the current evidence artifact.
- If the prepared mailbox count is not 120, stop and inspect the exact Gmail
  label query before changing anything; do not broaden the search.
