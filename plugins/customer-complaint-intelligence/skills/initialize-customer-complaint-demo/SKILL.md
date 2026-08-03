---
name: initialize-customer-complaint-demo
description: "Create the disposable Customer Complaint Demo as a real local Codex project in the user's existing Codex environment, ensure its required plugins are available, and open a welcome task. Use when a user asks to set up, bootstrap, or remove this demo. Do not seed or recreate Gmail fixture messages."
---

# Initialize Customer Complaint Demo

Create the demo as a separate local project, not as a separate Codex runtime.
Plugins, skills, and connector authentication belong to the invoking user's
Codex environment and may be shared with their other projects.

## Create

Inspect the installed plugins in the current Codex environment. Ensure these
are available, installing only those that are missing through their existing
official marketplaces:

- `customer-complaint-intelligence@jad-customer-complaint-intelligence`
- `gmail@openai-curated`
- `visualize@openai-bundled`

Tell the human when installing a missing shared plugin. Do not disconnect or
replace an existing connector account.

Run the bundled project creator:

```text
python3 scripts/initialize.py
```

It copies the bundled template to `~/Projects/Customer Complaint Demo` and
opens that path in Codex Desktop. If the project already exists, inspect its
marker and continue only when it is the valid generated demo; never overwrite
or silently repair another directory.

Use Codex's project and task tools to find the exact newly registered project,
then create and open one task in it. Ask the task to respond with exactly this
introduction, using the absolute clickable README path:

```text
Welcome to the Customer Complaint Demo. You can explore how Codex helps turn a crowded support inbox into a clearer understanding of what customers are experiencing—and move from insight to action.

Start with [README.md](ABSOLUTE_README_PATH).
```

Title the task `Customer Complaint Demo`. The task uses the current Codex
environment. If Gmail is already connected, the demo uses that connection. If
it is not connected, let Gmail surface its native connection flow on the first
Gmail request. Do not add a separate authentication ceremony.

Creating the welcome task is the final initialization action. Once task
creation succeeds, do not read the task back, resend the introduction, or
retry it for cosmetic formatting: the demo must open with one task containing
one introduction.

The `.eml` files are local scaffolding only. Do not send them, recreate Gmail
messages, or modify the mailbox during initialization.

## Remove

Only after the human explicitly asks to remove the demo, run:

```text
python3 scripts/remove.py --project-dir "$HOME/Projects/Customer Complaint Demo" --yes
```

The command checks the generated marker and removes only the local demo
project. It does not uninstall shared plugins, disconnect Gmail, remove tasks,
or change any other Codex project.
