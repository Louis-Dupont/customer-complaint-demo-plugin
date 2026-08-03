# Demo creation: methodology and learnings

This note records how the Northstar complaint demo was shaped and made reliable. It complements `DEMO.md`, which is the presentation runbook.

## What we set out to show

The demo had to make a familiar situation tangible: a team has too many customer complaints to read as a whole and cannot see what deserves attention. Codex does the heavy lifting across the full population, while the human asks the questions, inspects the evidence, makes the decision, and approves any operational change.

The resulting story is one connected progression:

1. Turn 120 unstructured Gmail complaints into a structured message register.
2. Combine that register with local customer context and visualize the patterns.
3. Trace one important pattern back to supporting emails and exceptions.
4. Let the human choose a handling rule, preview it, and apply Gmail labels.
5. Process one held-out complaint using the understanding already built.

Each step has standalone value, but the final steps reveal that the earlier outputs are reusable parts of one workflow—not isolated AI tricks.

## How the demo was shaped

We narrowed the setting before building it. One fictional company, one inbox, one customer table, one complaint register, and one decision kept the story understandable. We deliberately removed ideas that would have added more document types, departments, or business processes without strengthening the central experience.

We then designed the evidence backwards from the moment the audience should discover. The fixture contains broad complaint noise, with late delivery most visible by raw volume, while a more consequential short-delivery pattern emerges only after joining customer data: 23 hotel cases on the East route, plus 7 useful exceptions. A held-out complaint from the same cohort demonstrates reuse after the decision. These numbers are deterministic acceptance conditions, not facts the presenter has to manufacture during the demo.

The emails were generated from an explicit distribution, then varied in tone, phrasing, detail, severity, and consequence. The customer table was created as a separate local source so that the strongest insight could not be obtained from inbox text alone. This made the join and the deeper analysis materially useful.

The reusable plugin and the generated fictional client project remain separate artifacts:

- The installed plugin provides reusable skills plus an initializer.
- The initializer carries a frozen copy of this fictional template so a fresh installation can create the demo in one step.
- The created `Customer Complaint Demo` project contains the synthetic company, local mailbox fixtures, customer data, runbook, and reset tools.

The project deliberately uses the client's existing Codex environment. Installed plugins and connector authentication are shared at that environment level; only files, project context, tasks, and generated artifacts are project-specific.

## How the work was organized

The shared demo contract was defined before parallel implementation: the scenario, target insight, record schemas, handoff paths, expected cohort, and ownership of each step. Independent workstreams could then build the dataset, skills, Gmail setup, and verification without defining incompatible versions of the story.

The final authority remained the end-to-end rehearsal. Offline checks established fixture counts and the intended cohort, but the full run used the installed GitHub plugin, the connected Bobby Gmail account, the local customer CSV, real generated artifacts, visualization, label preview and approval, held-out reuse, and reset. An independent final audit then checked the handoff state.

## What we learned

- The strongest demo moment is not automation by itself. It is the shift from an inbox that is impossible to grasp manually to a business pattern the human can inspect and act on.
- Synthetic data needs a designed analytical structure as well as realistic prose. Realistic emails without a deliberate distribution would produce an attractive but inconclusive demo.
- A broad visible pattern followed by a less obvious joined-data pattern creates a credible analytical reveal. Exceptions make the investigation feel real and show that Codex can challenge the headline.
- Observable sender, subject, and timestamp fields are what let later steps re-find evidence and act. Connector IDs and invented links stay out of the handoff.
- A held-out case is a compact proof of reuse: the work produces an operating capability, not only a one-off report.
- The live service boundary should be the simplest one that supports the experience. The existing Gmail plugin was sufficient; a dedicated Google Cloud project and custom OAuth path added setup work without improving the actual demo, so that path was removed from the normal flow.
- Live connectors change details. Gmail normalized synthetic sender and date headers, so customer identity was kept in the body and the analysis avoided depending on timestamps. Sending to a fictional `.example` address created bounce notices; sending the held-out fixture to Bobby's own address avoided that noise.
- A reliable demo includes its starting state and reset state. The handoff is only complete when the next presenter can begin with 120 scoped messages, no action labels applied, the held-out message out of the active population, and an empty local workspace.
- A local Codex project is not a plugin or credential boundary. A separate `CODEX_HOME` can isolate CLI or app-server state, but Desktop tasks do not automatically adopt it merely because a project launcher points there.
- The simplest reliable client delivery is therefore a project inside the client's own Codex environment. Missing plugins are installed there, an existing Gmail connection is reused, and a missing connection is handled by Gmail's native flow on first use.
- Email population remains outside initialization. The local fixture makes the project reproducible, while the prepared Bobby inbox remains demo-only state.
