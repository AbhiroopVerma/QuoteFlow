# Demo readiness pack

Start with [the locked demo contract](DECISIONS.md), then inspect the
[six wireframes](wireframes.md), [source fixtures](fixtures.json) and
[25 golden cases](golden-cases.json).

The 15 September 2026 proposal supplied by the user is the design reference.
This pack deliberately narrows it to a local, synthetic, email-text-only demo.
It contains specifications and fixtures, not a QuoteFlow application. Existing
gateway examples in the repository are not the quotation implementation.

## What is decided

Scope, exact SKUs, customer, seller, currency, input format, rounding, pricing,
approval boundaries, file rejection, role permissions, logging fields, spend
limits and six screen layouts are specified. Defaults were selected under the
user's delegated design authority, not represented as SME-approved policy.

## What still needs a person

Actual team names and runtime account identities are unassigned. Shared-account
balance and available allocation are unverified. These are real outstanding
facts; no guessed names or balances are embedded. Paid execution remains off.

## Implementation sequence

1. Load versioned fixtures; implement deterministic calculations and policy.
2. Add case revisions, permissions, consent and approval state transitions.
3. Build Inbox, Resolve and Price with deterministic replay first.
4. Connect bounded extraction/matching through the existing gateway only after
   budget and credentials are privately configured; preserve offline replay.
5. Add Approve, Preview, reconciled PDF export and measured Dashboard.
6. Run the golden cases against the application, then access-control, file
   rejection, budget race/restart, idempotency and document reconciliation tests.

The golden set is an initial representative suite, not exhaustive test coverage.
Before application release add direct probes for 92% confidence, 5%+epsilon,
20%-epsilon margin, exactly/above SGD 100,000 total, union of approval roles,
exact freshness cutoffs, expired/conflicting prices, retries, invalid quantities,
zero prices and concurrent approval edits. Security and budget enforcement
require executable integration tests; prose assertions do not prove enforcement.

Run `python3 docs/demo/verify_fixtures.py` to check fixture structure, catalogue
references and the explicitly enumerated monetary expectations. This is a
consistency check of the acceptance data only; it does not execute extraction,
workflow, rendering, security or a live model. Application evaluation must report
these separately and must not count this checker as 25 passed application tests.
