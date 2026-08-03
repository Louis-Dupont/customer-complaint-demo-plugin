# Demo setup

The setup files belong to the fictional demo environment, not to the reusable
Codex plugin.

## Generate or reset local fixtures

Run these commands from the demo folder:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r setup/requirements.txt
python3 setup/generate_demo_data.py
python3 setup/reset_demo.py
python3 setup/check_fixture.py
```

The generator is deterministic. It rewrites `data/customers.csv`, the `.eml`
fixtures, and `setup/fixture-manifest.csv`.

## Gmail starting state

The normal demo does not require a Google Cloud project or a local Gmail API
credential. Bobby's connected Gmail account is already populated with the 120
synthetic messages and the `Demo/Northstar Complaint Demo` label. The skills
read and update that mailbox through the official Gmail plugin.

Verify the starting state in Codex with the Gmail plugin using:

```text
Search Gmail for `label:"Demo/Northstar Complaint Demo" -in:trash` and confirm
that it contains 120 messages in bobby.shan010@gmail.com.
```

If the mailbox ever has to be rebuilt without Gmail API credentials, use a
fresh Codex task with the Gmail plugin and this bounded setup prompt:

```text
Read the 120 files in inbox-fixture/emails/ in this demo folder. For each file,
send one synthetic message to bobby.shan010@gmail.com using the file's subject
and plain-text body, prefixing the subject with [DEMO]. Create or reuse the
label Demo/Northstar Complaint Demo and apply it to every message. Do not send
to any other address, do not read or modify unrelated mail, and verify that
the label contains exactly 120 messages when finished. Do not include the
held-out file; it is loaded separately in the reuse step.
```

This is demo preparation only. The message sender will be Bobby because Gmail
does not allow the connected account to impersonate fictional customers; the
customer name and reference remain in each synthetic body. The normal handoff
starts with the already-prepared mailbox, so rebuilding is optional.

The fixture loader below is optional developer scaffolding, not a prerequisite
for presenting the demo. It uses a separately managed Gmail API credential and
must not be treated as part of the client-deliverable plugin.

### Optional API seeder

If an operator explicitly chooses to rebuild a mailbox through the API, use a
Desktop OAuth client JSON kept outside this folder:

```sh
python3 setup/seed_gmail.py --credentials /path/to/credentials.json
```

The JSON must be from a project with the Gmail API enabled, Bobby allowed as an
OAuth test user, and the Gmail modify scope enabled. Keep it outside this
folder and use synthetic mail only. The API seeder and reset helper verify the
profile is `bobby.shan010@gmail.com` and refuse any other account.

The legacy ADC variant is retained for development but is not the normal demo
path; Google's SDK OAuth client may block the Gmail restricted scope.

To load the held-out message through the optional API path after the main
demonstration:

```sh
python3 setup/seed_gmail.py \
  --credentials /path/to/credentials.json \
  --include-held-out
```

If the held-out message was reset previously, this command untrashes and
reuses its recorded Gmail message ID. It does not create a duplicate copy.

The seed command also writes `setup/gmail-seed-receipt.json` (ignored by Git),
which records the exact fixture files, message IDs, thread IDs, hashes and
container label used in that load.

To reset Gmail-owned API-seeded state, including the held-out message:

```sh
python3 setup/reset_gmail.py --credentials /path/to/credentials.json
python3 setup/reset_demo.py
```

Together, the two reset commands only touch message IDs recorded in
`gmail-fixture-state.json`. Gmail reset removes the action labels and the
`Demo/Northstar Complaint Demo` container label from those known messages,
restores main messages to INBOX and UNREAD, and moves the held-out message to
Trash. It never permanently deletes a Gmail message. The user-label
definitions are preserved; reset removes the action and container labels only
from the exact recorded fixture messages, so a label someone reused elsewhere
is not globally deleted. The reset writes
`setup/gmail-reset-receipt.json` (ignored by Git) with the exact message and
label provenance. The local reset clears generated workspace files separately.
