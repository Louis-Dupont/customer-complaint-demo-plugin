# Fictional customer complaint demo environment

This folder is deliberately separate from the GitHub plugin repository. It is
a dummy client environment used to rehearse and record the demonstration.

The fictional company is a linen-delivery service for hotels, restaurants and
spas. The starting state is a local customer CSV and an untagged Gmail inbox
containing realistic complaint fixtures. Codex writes generated artifacts into
`workspace/` as each bounded skill is invoked.

## Handoff prerequisites

The operator needs:

- Codex with the reusable plugin installed and the dedicated Gmail account
  connected through the official Gmail plugin.
- The prepared Bobby mailbox. It contains 120 synthetic messages under
  `Demo/Northstar Complaint Demo` and needs no Google Cloud project or local
  API credential to run the demo.

The local `.eml` fixtures and setup helpers are demo scaffolding for rebuilding
or checking the fictional dataset. They are separate from the plugin and no
credential is included in this folder.

## Folder map

- `company.md`: the small amount of context a demo operator may show.
- `data/customers.csv`: local customer context used by the analysis skill.
- `inbox-fixture/emails/`: reproducible `.eml` messages used to seed Gmail.
- `setup/`: demo-only generation, seeding and reset helpers.
- `workspace/`: starts empty and receives the real skill handoffs.

## Starting the demo

1. Install/connect the official Gmail plugin if needed:
   `codex plugin add gmail@openai-curated`.
2. Connect the dedicated Gmail account through the Gmail plugin.
3. Run the setup helper described in `setup/README.md`.
4. Start a fresh Codex task with both plugins installed.
5. Follow `DEMO.md`.
