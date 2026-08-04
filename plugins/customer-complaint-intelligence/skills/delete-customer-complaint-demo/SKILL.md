---
name: delete-customer-complaint-demo
description: "Delete the generated local Customer Complaint Demo folder and archive Codex tasks rooted in that exact folder so the demo can be initialized again from a clean filesystem state. Use only when the human explicitly asks to delete, remove, or clean up this demo. Do not touch Gmail, shared plugins, connector authentication, or unrelated Codex projects."
---

# Delete Customer Complaint Demo

Remove only the disposable project created by
`initialize-customer-complaint-demo`. Run this skill from another Codex project,
because the target folder will disappear.

## Procedure

1. Use `~/Projects/Customer Complaint Demo` unless the human explicitly gives
   another path. Resolve it to an absolute path.
2. List Codex projects and identify, when present, the one whose local path
   exactly equals the target. Do not select a project by title alone.
3. List Codex tasks and collect only tasks whose `cwd` exactly equals the
   target path. Do not use prefix or title matching.
4. From this skill directory, preview the guarded deletion:

   ```text
   python3 scripts/delete_demo.py --project-dir "<absolute target>"
   ```

   Continue only when the command identifies exactly the intended generated
   demo directory. It validates the marker and does not delete during preview.
5. Delete the folder:

   ```text
   python3 scripts/delete_demo.py --project-dir "<absolute target>" --yes
   ```

6. After successful deletion, archive the exact tasks collected in step 3 when
   Codex task archiving is available. Archiving is recoverable and prevents old
   demo runs from cluttering the next rehearsal. Do not archive the invoking
   task when it belongs to another project.

Codex currently provides no supported project-record deletion operation. Do
not edit Codex's private state files. The saved sidebar project may remain and
will be reused when the same folder is initialized again.

## Boundaries

- Require an explicit human deletion request; never invoke this skill implicitly.
- Refuse an unmarked directory, a symbolic link, a mismatched marker, or a
  marker that points elsewhere.
- Delete no Gmail messages, labels, fixture mail, plugins, connector
  authentication, Codex configuration, or unrelated tasks.
- If the folder is already absent, report that no local files were removed;
  archive only tasks whose exact recorded `cwd` matches the intended path.
- Stop if any target is ambiguous or any deletion check fails.

Finish by reporting the deleted path, the tasks archived, and the fact that
shared Codex and Gmail state was preserved. State whether the saved sidebar
project record remains available for reuse.
