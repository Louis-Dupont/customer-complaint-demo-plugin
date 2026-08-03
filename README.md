# Customer Complaint Intelligence

This repository is the client-deliverable Codex plugin. It contains four
reusable complaint-workflow skills and an explicit initializer for an isolated
fictional demo capsule. The initializer carries the demo template as an asset;
the generated project and its Codex runtime remain separate from this plugin.

## Install in Codex

```sh
codex plugin marketplace add Louis-Dupont/customer-complaint-demo-plugin
codex plugin add customer-complaint-intelligence@jad-customer-complaint-intelligence
```

The repository is expected to be public at
`https://github.com/Louis-Dupont/customer-complaint-demo-plugin` so a
coworker can run these commands without a separate service or credential.

Start a new Codex task after installation.

## Initialize the demo capsule

From a fresh Codex environment, invoke
`$customer-complaint-intelligence:initialize-customer-complaint-demo`.
It creates `Customer Complaint Demo` and a dedicated
`~/.codex-products/customer-complaint-demo`, installs the complaint plugin,
Gmail, and `@visualize` into that home, then opens a short welcome task linked
to the demo README. Codex and Gmail surface their native connection flows only
if needed; Gmail is first requested during the demo. The initializer does not
send or recreate the synthetic Gmail messages.

## Requirements

- Codex.
- The official Gmail plugin connected to the intended Gmail account. If it is
  not installed yet, run `codex plugin add gmail@openai-curated`, then start a
  fresh Codex task and complete the Gmail connection.
- The bundled `@visualize` capability for interactive analysis.
- A local customer CSV for the analysis step.

## Skills

- `extract-gmail-complaints`: turn complaint threads into a source-linked CSV.
- `analyze-complaint-patterns`: join the register with customer data and build analysis artifacts.
- `investigate-complaint-evidence`: inspect one finding through supporting and contradictory source emails.
- `apply-complaint-labels`: preview and apply an explicitly approved Gmail-labeling decision.
- `initialize-customer-complaint-demo`: create or remove the isolated demo capsule.

The human invokes each skill separately. No skill runs the complete workflow or
chooses the business decision silently.

There is no custom MCP server, hosted JAD service, plugin-specific login, or
background automation in this repository.
