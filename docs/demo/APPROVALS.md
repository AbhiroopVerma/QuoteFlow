# Demo approval workflow

Continue on `codex/working-demo`; keep `main` unchanged.

This increment implements a rehearsal of the proposal's human approval loop.
Three explicitly synthetic personas represent Sales Administrator, Sales Manager
and Finance Approver. A persona selector is not authentication: anyone with local
access can select any persona. Do not use it as real business authorization.
The server maps an allowlisted persona ID to its role, never accepts a role or
an approved flag from the quote payload, and checks each action itself.

The administrator creates/edits quotes, records consent and requests approvals.
Requests bind every required role to the current revision and a commercial-input
hash including the fixture/rule version. Approvers can approve or reject only
their role's pending task, with a required reason. They cannot edit quote inputs
or perform the final administrator review. A requester's own persona cannot
decide its request. Rejected quotes require a new revision. Repeated identical
decisions are idempotent; contradictory or stale decisions are rejected.

Any edit invalidates the current approvals and final review. The administrator
must request approvals again for the new revision. All required roles must pass;
product and delivery blockers cannot be overridden by approval.

SQLite stores append-only revision-input snapshots alongside decision events in
case history. The app has no endpoint to edit snapshots. This is application-level
history, not a tamper-proof or externally signed production audit store. Existing
cases gain only their current snapshot; earlier lost inputs are not reconstructed.
Deleting a demo case explicitly deletes its snapshots too.

Implementation: test `app/backend/workflow.py` independently; extend API permission and
concurrency tests; connect persona selection and request/decision controls; show
snapshot history; run the browser approval path; update setup documentation;
commit and push this same branch. No model calls or external sends are introduced.
