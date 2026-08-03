---
name: initialize-customer-complaint-demo
description: "Create the disposable Customer Complaint Demo project from the bundled template, give it an isolated CODEX_HOME, install its plugin dependencies there, and open it. Use when a user asks to set up, bootstrap, or remove this demo environment. Do not seed or recreate the Gmail fixture messages."
---

# Initialize Customer Complaint Demo

Use this skill as the bootstrapper for a fresh demo capsule. The generated
project and its Codex home are separate from the environment that invoked this
skill.

## Create

Run the bundled command from this skill directory:

```text
python3 scripts/initialize.py
```

It creates `Customer Complaint Demo` under `~/Projects` and its isolated
runtime under `~/.codex-products/customer-complaint-demo`. It copies the
bundled fictional project, installs the complaint plugin, Gmail, and
`@visualize` into the new home, writes a launcher, and opens the project.

If either target already exists, stop without overwriting it. The command
stops on the first failed setup operation; do not add a second inspection pass
or try to repair a partial capsule silently.

The new home has its own Codex login and connector state. Ask the human to
authenticate and connect Gmail inside that new environment. Never copy tokens
from the invoking home.

The `.eml` files in the bundled project are local scaffolding only. Do not send
them, recreate the Gmail messages, or modify the live mailbox as part of
initialization.

## Remove

Only after the human explicitly asks to remove the demo, run:

```text
python3 scripts/remove.py --project-dir "$HOME/Projects/Customer Complaint Demo" --yes
```

Run removal from the original Codex environment, not from the capsule being
deleted. The command checks the generated capsule marker and removes exactly
the project directory and its dedicated runtime. It does not remove the
plugin, Gmail data, or any other Codex home.
