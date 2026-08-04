# Customer Complaint Intelligence

This repository is the client-deliverable Codex plugin. It contains four
reusable complaint-workflow skills and two lifecycle skills for a fictional
local demo project. The initializer carries the template as an asset; the
generated project remains separate from the plugin installation.

## Install in Codex

```sh
codex plugin marketplace add Louis-Dupont/customer-complaint-demo-plugin
codex plugin add customer-complaint-intelligence@jad-customer-complaint-intelligence
```

The repository is expected to be public at
`https://github.com/Louis-Dupont/customer-complaint-demo-plugin` so a
coworker can run these commands without a separate service or credential.

Start a new Codex task after installation.

## Initialize the demo project

From a fresh Codex environment, invoke
`$customer-complaint-intelligence:initialize-customer-complaint-demo`.
It creates `Customer Complaint Demo` and a dedicated
local project, ensures Gmail and `@visualize` are available in the current
Codex environment, then opens a short welcome task linked to the demo README.
If Gmail is already connected, that connection is reused; otherwise Gmail
surfaces its native connection flow on first use. The initializer does not send
or recreate the synthetic Gmail messages.

Plugins and connector authentication belong to the user's Codex environment,
not exclusively to this project. Removing the demo deletes only its local
project files.

To clean up before another rehearsal, invoke
`$customer-complaint-intelligence:delete-customer-complaint-demo` from another
project. It deletes only the marked local demo folder and archives tasks rooted
at that exact path when task archiving is available. Codex may retain the saved
sidebar project record and reuse it when the same path is initialized again.

## Requirements

- Codex.
- The official Gmail plugin connected to the intended Gmail account. If it is
  not installed yet, run `codex plugin add gmail@openai-curated`, then start a
  fresh Codex task and complete the Gmail connection.
- The bundled `@visualize` capability for interactive analysis.
- A local customer CSV for the analysis step.

## Skills

- `extract-gmail-complaints`: turn complaint emails into a structured CSV.
- `analyze-complaint-patterns`: map the full inbox, then guide a human-selected pattern deep dive.
- `investigate-complaint-evidence`: inspect one finding through supporting and contradictory source emails.
- `apply-complaint-labels`: preview and apply an explicitly approved Gmail-labeling decision.
- `initialize-customer-complaint-demo`: create the local demo project.
- `delete-customer-complaint-demo`: delete the marked demo folder and archive its demo tasks.

In the marked demo project, the workflow skills also carry the demo's defined
scope and handoff paths, so they can be invoked without repeating setup
details. The human still invokes each skill separately, inspects the outputs,
and approves the Gmail write-back; no skill runs the complete workflow or
chooses the business decision silently.

There is no custom MCP server, hosted JAD service, plugin-specific login, or
background automation in this repository.
