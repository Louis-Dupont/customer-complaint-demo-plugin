---
name: apply-complaint-labels
description: Apply an explicitly approved complaint-handling decision to Gmail by previewing the exact matching threads, creating or reusing the requested labels, and recording the result. Use after complaint analysis and human review when the user asks to operationalize a selected rule. Do not use to discover patterns, invent the business decision, or label messages without approval.
---

# Apply Complaint Labels

This skill exists to turn a human-approved complaint-handling decision into a controlled Gmail change. The analysis and investigation remain separate responsibilities; this skill starts only when the human has chosen the rule and asks for the operational change.

## Readiness

Require:

- A clear human decision describing which messages or threads should receive which label.
- A complaint register or investigation artifact that identifies the matching Gmail threads.
- An active Gmail connection with permission to create and apply labels.

If the decision or target set is ambiguous, stop and ask for the missing boundary instead of inferring it from the analysis.

## Procedure

1. Restate the proposed labels, matching rule, and target count.
2. Resolve the exact Gmail thread IDs from the current register or evidence artifact.
3. Expand each approved thread with `gmail_read_email_thread` and collect
   every message ID in that thread. The label tool operates on message IDs, not
   thread IDs; preserve both identifiers in the preview and receipt.
4. Show a preview containing the labels, every target thread, its expanded
   message IDs, and links where available.
5. Ask the human to approve the preview.
6. After approval, call Gmail's `gmail_apply_labels_to_emails` with the exact expanded
   message IDs, the approved label names as arrays, and
   `create_missing_labels: true`.
7. Write a compact operation receipt to `workspace/actions/` containing the
   rule, approval, applied labels, thread IDs, message IDs, and timestamp.

Do not send, archive, delete, or modify message content. Do not apply a broader Gmail search than the approved target set.

## Receipt contract

Write one JSON receipt under `workspace/actions/` containing:

- `decision`: the human-approved matching rule.
- `label_names`: the exact labels requested.
- `approved`: whether the human approved the preview.
- `thread_ids`: the approved Gmail thread IDs.
- `message_ids`: the expanded Gmail message IDs sent to the label tool.
- `applied_message_ids`: the IDs reported as changed by Gmail.
- `unapplied_message_ids`: any IDs that could not be changed and why.
- `created_label_names`: labels created during this operation, if the connector reports that information.
- `timestamp`: an ISO 8601 operation timestamp.

## Stop

Stop after the preview if the human does not approve. Stop after the receipt is written and report any thread that could not be changed. A successful run means the applied message set equals the approved preview set.
