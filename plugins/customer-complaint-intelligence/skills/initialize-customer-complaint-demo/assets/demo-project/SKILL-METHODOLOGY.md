# Skill creation: methodology and learnings

This note records how the reusable skills behind the Northstar demo were designed. It concerns the plugin contracts, not the fictional data or presentation choreography.

## The chosen skill shape

An early risk was to create one or two end-to-end skills that silently performed the whole demo. That would have hidden the human's role, coupled unrelated responsibilities, and made the plugin harder to reuse.

Instead, we used the natural handoffs in the work as the skill boundaries:

1. `extract-gmail-complaints`: Gmail population to a validated, source-linked complaint CSV.
2. `analyze-complaint-patterns`: complaint CSV plus customer CSV to reproducible joined tables, findings, and an interactive visualization.
3. `investigate-complaint-evidence`: one human-selected finding to a source-backed brief with supporting cases and exceptions.
4. `apply-complaint-labels`: one approved handling rule to a previewed Gmail change and operation receipt.

No skill owns the full workflow. The user can invoke one step, inspect its output, ask an ordinary follow-up question, or continue to the next skill. The demo sequence lives in the demo runbook rather than inside the plugin.

## How each contract was written

Each skill was treated as a concise responsibility contract. It states:

- why the capability exists;
- the inputs it is allowed to rely on;
- the semantic meaning and exact shape of its output;
- the procedure only where consistency matters;
- what it explicitly must not do;
- the condition at which it is complete and must stop.

The frontmatter description carries both positive and negative triggers because it decides when Codex loads the skill. The body concentrates on non-obvious rules rather than explaining things Codex can already reason through.

The handoff contracts preserve `case_id`, `thread_id`, `customer_id`, and `source_url`. Those fields make the chain inspectable from Gmail to analysis, evidence, and write-back. The contracts also keep messages, threads, complaint cases, and customers distinct; collapsing those units would have changed the analysis.

## Where determinism was used

We left semantic work to the model: interpreting varied complaint language, normalizing categories, exploring patterns, explaining evidence, and answering the human's follow-up questions.

Small scripts were added only where deterministic behavior protected a boundary:

- extraction validates the exact CSV schema, identifiers, values, and row integrity;
- analysis validates and joins the two datasets, then emits reproducible summary tables;
- Gmail write-back requires an exact preview, explicit human approval, and a receipt.

This kept the skills light while making fragile handoffs testable. The scripts support the contracts; they do not replace the AI work.

## How the skills were validated

Validation happened at three levels:

1. Contract tests checked plugin structure, metadata, scripts, and required boundaries.
2. A fresh GitHub installation confirmed that the published plugin was the artifact being tested.
3. The skills were exercised in sequence against the live synthetic mailbox and local customer table, including visualization, evidence retrieval, Gmail labeling, held-out reuse, and cleanup.

The live rehearsal exposed details that static review did not: Gmail search returns messages while the analysis is case-based; label operations require message IDs even when the decision is expressed over threads; visualization needs a bounded, explicit handoff; and output paths must remain stable across separate Codex turns.

## What we learned

- A useful skill boundary is a reusable handoff, not a chapter in the demo story and not an entire business outcome.
- The output contract is often more valuable than a long procedure. Once the handoff is precise, Codex retains freedom to handle varied real inputs.
- Explicit exclusions prevent helpful overreach. Extraction does not analyze, analysis does not read Gmail, investigation does not choose the action, and labeling does not invent the rule.
- Human authority belongs at the consequential transition. Codex can prepare evidence and the exact target set; the person chooses and approves the operational change.
- Generic plugin contracts and demo-specific expectations must remain separate. The skill never encodes “23 East-route hotel cases”; the fixture and runbook do.
- Real forward use is part of skill design. Several important contract refinements appeared only when one skill's actual output became the next skill's input.
- The four skills form a system through explicit artifacts, not through an orchestrator skill. That makes every step independently useful and keeps ordinary conversation available between them.
