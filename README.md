# Customer Complaint Intelligence

This repository is the client-deliverable Codex plugin. It contains reusable
skills only; it does not contain a fictional company, demo emails, customer
data, Gmail fixture loaders, or presentation material.

## Install in Codex

```sh
codex plugin marketplace add <github-owner>/customer-complaint-intelligence-plugin
codex plugin add customer-complaint-intelligence@jad-customer-complaint-intelligence
```

Start a new Codex task after installation.

## Requirements

- Codex.
- The Gmail plugin connected to the intended Gmail account.
- The bundled `@visualize` capability for interactive analysis.
- A local customer CSV for the analysis step.

## Skills

- `extract-gmail-complaints`: turn complaint threads into a source-linked CSV.
- `analyze-complaint-patterns`: join the register with customer data and build analysis artifacts.
- `investigate-complaint-evidence`: inspect one finding through supporting and contradictory source emails.
- `apply-complaint-labels`: preview and apply an explicitly approved Gmail-labeling decision.

The human invokes each skill separately. No skill runs the complete workflow or
chooses the business decision silently.
