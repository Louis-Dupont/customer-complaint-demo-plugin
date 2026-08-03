# Demo creation: methodology and learnings

This note records how the Northstar complaint demo was shaped and made reliable. It complements `DEMO.md`, which is the presentation runbook.

## What we set out to show

The demo had to make a familiar situation tangible: a team has too many customer complaints to read as a whole and cannot see what deserves attention. Codex does the heavy lifting across the full population, while the human asks the questions, inspects the evidence, makes the decision, and approves any operational change.

The resulting story is one connected progression:

1. Turn 120 unstructured Gmail complaints into a source-linked register.
2. Combine that register with local customer context and visualize the patterns.
3. Trace one important pattern back to supporting emails and exceptions.
4. Let the human choose a handling rule, preview it, and apply Gmail labels.
5. Process one held-out complaint using the understanding already built.

Each step has standalone value, but the final steps reveal that the earlier outputs are reusable parts of one workflow—not isolated AI tricks.

## How the demo was shaped

We narrowed the setting before building it. One fictional company, one inbox, one customer table, one complaint register, and one decision kept the story understandable. We deliberately removed ideas that would have added more document types, departments, or business processes without strengthening the central experience.

We then designed the evidence backwards from the moment the audience should discover. The fixture contains broad complaint noise, with late delivery most visible by raw volume, while a more consequential short-delivery pattern emerges only after joining customer data: 23 hotel cases on the East route, plus 7 useful exceptions. A held-out complaint from the same cohort demonstrates reuse after the decision. These numbers are deterministic acceptance conditions, not facts the presenter has to manufacture during the demo.

The emails were generated from an explicit distribution, then varied in tone, phrasing, detail, severity, and consequence. The customer table was created as a separate local source so that the strongest insight could not be obtained from inbox text alone. This made the join and the deeper analysis materially useful.

The reusable plugin and the generated fictional client environment remain separate at runtime:

- The installed plugin provides reusable skills plus an initializer.
- The initializer carries a frozen copy of this fictional template so a fresh installation can create the demo in one step.
- The created `Customer Complaint Demo` project contains the synthetic company, local mailbox fixtures, customer data, runbook, and reset tools; its dedicated `CODEX_HOME` contains its own plugins and credentials.

Bundling the template changed the packaging boundary, not the operating boundary: skills never read fixture data from inside their own installation, and the working project is still a distinct client-like environment that can be removed as one capsule.

## How the work was organized

The shared demo contract was defined before parallel implementation: the scenario, target insight, record schemas, handoff paths, expected cohort, and ownership of each step. Independent workstreams could then build the dataset, skills, Gmail setup, and verification without defining incompatible versions of the story.

The final authority remained the end-to-end rehearsal. Offline checks established fixture counts and the intended cohort, but the full run used the installed GitHub plugin, the connected Bobby Gmail account, the local customer CSV, real generated artifacts, visualization, label preview and approval, held-out reuse, and reset. An independent final audit then checked the handoff state.

## What we learned

- The strongest demo moment is not automation by itself. It is the shift from an inbox that is impossible to grasp manually to a business pattern the human can inspect and act on.
- Synthetic data needs a designed analytical structure as well as realistic prose. Realistic emails without a deliberate distribution would produce an attractive but inconclusive demo.
- A broad visible pattern followed by a less obvious joined-data pattern creates a credible analytical reveal. Exceptions make the investigation feel real and show that Codex can challenge the headline.
- Stable identifiers and source links are what connect analysis back to evidence and later action. Without them, the workflow becomes a sequence of summaries.
- A held-out case is a compact proof of reuse: the work produces an operating capability, not only a one-off report.
- The live service boundary should be the simplest one that supports the experience. The existing Gmail plugin was sufficient; a dedicated Google Cloud project and custom OAuth path added setup work without improving the actual demo, so that path was removed from the normal flow.
- Live connectors change details. Gmail normalized synthetic sender and date headers, so customer identity was kept in the body and the analysis avoided depending on timestamps. Sending to a fictional `.example` address created bounce notices; sending the held-out fixture to Bobby's own address avoided that noise.
- A reliable demo includes its starting state and reset state. The handoff is only complete when the next presenter can begin with 120 scoped messages, no action labels applied, the held-out message out of the active population, and an empty local workspace.
- A self-contained initializer is useful only when it creates a genuinely separate environment. The tested flow copies the project, creates a new `CODEX_HOME`, installs the required plugins there, refuses existing targets, and removes the generated project and runtime together.
- Marketplace configuration may store absolute source paths. Sources that must survive initialization need to be placed at their final location before plugin installation; moving the runtime afterward breaks the new environment.
- Email population is intentionally outside initialization. The local fixture makes the project reproducible, while authentication and the dedicated Bobby inbox remain visible setup boundaries for the presenter.
