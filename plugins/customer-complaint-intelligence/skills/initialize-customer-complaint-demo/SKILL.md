---
name: initialize-customer-complaint-demo
description: "Create the disposable Customer Complaint Demo project from the bundled template, give it an isolated CODEX_HOME, install its plugin dependencies, and open a welcome task. Use when a user asks to set up, bootstrap, or remove this demo environment. Do not seed or recreate the Gmail fixture messages."
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
`@visualize` into the new home, and writes a launcher.

If the command reports that the project already exists, inspect the project
and runtime markers. Continue to the welcome task only when both markers
identify the same valid Customer Complaint Demo capsule. Never overwrite or
silently repair an existing project or partial capsule.

Do not add a separate authentication ceremony or preflight login check. Let
Codex surface its native flow if authentication is needed. Gmail connection is
also deferred until the first Gmail request in the demo; let the Gmail plugin
surface its normal connection flow at that moment. Never copy credentials from
the invoking environment.

## Open the welcome task

After initialization, create one persisted Codex task with the generated
project as its working directory and the generated runtime as `CODEX_HOME`.
Ask that task to respond with exactly this introduction, using an absolute
clickable path for the README:

```text
Welcome to the Customer Complaint Demo. You can explore how Codex helps turn a crowded support inbox into a clearer understanding of what customers are experiencing—and move from insight to action.

Start with [README.md](ABSOLUTE_README_PATH).
```

Open that new task for the human. If Codex presents its native authentication
flow while the task is created, let the human complete it and then retry. If
task creation returns an unauthorized response instead of opening that flow,
open the generated project with `codex-project` so Desktop can present its
native sign-in; ask the human to complete it, then retry the welcome task. Do
not run a preflight login check, copy credentials, or build custom
authentication. The generated project is intentionally not a Git repository;
when the task is created through the CLI, allow that project with Codex's
supported non-Git option.

Stop only when the welcome task is open or the native Desktop sign-in requires
the human's attention.

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
