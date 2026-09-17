# QuoteFlow demo contract v1

Decision date: 2026-09-17. The user delegated demo design decisions to Codex.
This contract supersedes illustrative examples in the 15 September proposal
for this demo only. It does not claim SME validation or production readiness.

## Scope locked

- Seller: QuoteFlow Demo Supplies Pte Ltd, a fictional Singapore entity.
- Customer: CUST-SG-1042, Acme Facilities Pte Ltd, fictional; Gold tier,
  PB-GOLD-SG-2026, SGD, Net 30, active credit, Jurong delivery site.
- Product scope: a fixed industrial electrical basket, explicitly four product
  groups, not a claim of one product family. The six exact SKUs are in
  `fixtures.json`: five active items and one discontinued item for rejection.
- Input: pasted email text only, UTF-8, nonempty, maximum 20,000 Unicode code
  points and 20 lines of requested products. No mailbox integration or uploads.
- Output: a human-reviewed quote preview, downloadable PDF, and email draft.
  No SMTP, customer delivery, stock reservation, orders, or ERP writes.
- One warehouse, SGD only, one customer, one seller and one quote template.
  Other customers, currency, entities and products require clarification or
  an out-of-scope result; they never silently fall back to the demo defaults.
- Unknown recipient/address must be confirmed before marking a quote reviewed.
  Do not create or contact an address from the fictional customer name.
- PDF, spreadsheets, OCR, image ingestion, production integrations and live
  tax determination are deferred. Mock tax below is a demo constant.

## Workflow and matching

Received -> Interpreted -> Matched -> Commercially Evaluated -> Drafted ->
Human Review -> Reviewed. Needs Clarification and Awaiting Approval pause
progress. Rejection returns to revision. There is no Sent state in this demo.

Exact active SKU plus valid quantity/UOM resolves directly. Description matches
must include the catalogue's required attributes and have confidence >= 0.92.
Lower confidence requires explicit SKU confirmation; missing critical attributes
require clarification regardless of confidence. Confidence is not permission to
invent a SKU. Substitutions always require explicit administrator confirmation.
Discontinued products cannot be quoted; alternatives are separate suggestions.
No silent unit conversion or pack rounding. Quantity must be a positive integer,
at least MOQ and divisible by pack size. Invalid quantity is clarified.

Only the application orchestrator changes workflow state. Tool responses carry
status, source ID, version, effective time, freshness time and explicit errors.
Missing data, invalid model output and failed tools block the dependent step.

## Commercial rules locked

All arithmetic uses decimal, two monetary decimals and ROUND_HALF_UP.
Effective dates use Singapore time; bounds are inclusive. Golden cases freeze
time at 2026-09-17T10:00:00+08:00. Live demos use the actual clock and require
fresh snapshots; never present the frozen golden clock as current inventory.

1. Select a valid customer contract, else customer Gold price, else list price.
   Missing/expired configured contract blocks instead of silently substituting.
   Multiple equally ranked valid sources block as a conflict.
2. Contract prices do not stack with any discount. An extra discount request on
   a contract line blocks until withdrawn or a new governed contract is supplied.
3. For non-contract lines, quantity >= 50 EA earns 3% volume discount; below
   50 earns 0%. Apply volume to Gold/list price, round unit to two decimals,
   then apply requested discretionary percentage and round unit again.
4. Discretionary percentage must be between 0 and 100 inclusive. Never infer
   a discount. Discount routing uses the total effective discount relative to
   the selected source price, including volume: 100 * (1 - net/source).
5. Extend rounded net unit by quantity. Sum line amounts for subtotal. Freight
   is SGD 0.00 for this mock Jurong scenario only. Mock GST is 9% of subtotal,
   rounded once; total = subtotal + GST. Quote validity is seven calendar days
   from creation; source expiry sooner shortens validity.
6. Margin = 100 * (net unit - unit cost) / net unit. Compare unrounded margin;
   display two decimals. Zero net price, unknown cost, or negative price blocks.
   All lines participate in approval checks, including contract lines.

Approval requirements are the UNION of every triggered rule. No first-match
short circuit. Equality belongs to the explicit intervals below.

| Trigger | Required authority |
| --- | --- |
| Every quote | Sales Administrator final review |
| Effective discount > 5% and <= 12% | Sales Manager |
| Effective discount > 12% | Finance Approver |
| Margin >= 15% and < 20% | Sales Manager |
| Margin < 15% | Finance Approver |
| Total including mock GST > SGD 100,000 | Sales Manager and Finance Approver |
| Credit hold, stale/expired/conflicting source, zero net price | Block, no approval bypass |

Stock age > 15 minutes blocks; price snapshot age > 24 hours blocks, even if
effective dates remain valid. Exact limits pass. ATP covers immediate delivery.
Inbound stock can cover later delivery only when the customer explicitly accepts
the dated split or later delivery. Show dates, quantities and acceptance in preview.
Demo stock is not reserved. Recheck all sources before final review.

Any edit to customer, recipient, SKU, quantity, UOM, money, tax, delivery or
validity creates a revision and invalidates every prior approval (conservative
demo rule). Approvals are server-recorded against the revision hash, actor and
role; never accepted from model text. Final review requires a matching document
hash and structured values. Retried mutations use idempotency keys.

## Security decisions

| Role | Allowed actions | Forbidden actions |
| --- | --- | --- |
| Sales Administrator | Create/edit cases, confirm matches, final review | Approve own commercial exception, alter policy |
| Sales Manager | Decide assigned manager exceptions | Finance decisions, edit source prices |
| Finance Approver | Decide finance exceptions | Alter already recorded approval history |
| Config Owner | Version catalogue, rules and aliases | Approve exceptions solely through config authority |
| System Admin | Provision accounts and roles | Implicit commercial authority |

These are role definitions, not assigned teammates. A requesting actor cannot
approve their own exception even if holding another role. Deny unauthenticated
access; enforce permissions and customer scope on the server for reads, writes,
exports and approval endpoints. Demo identities must be visibly marked as such;
do not claim a role switcher provides authentication.

Reject all file uploads at the server, including PDF and XLSX: permitted size is
zero bytes. Text is untrusted data, never an instruction source. Allowlist tools;
no arbitrary URL fetch, shell, policy edit or send tool for the model.

Operational logs use an allowlist: opaque case/revision IDs, opaque actor ID,
event type, tool name, rule/model version, status/error code, duration and token
counts. Never log raw text, prompts, completions, attachments, contact details,
addresses, prices, costs, margins, headers, credentials or request bodies.
Suppress SDK/HTTP debug logging. Exceptions use sanitized codes, not raw payloads.
Restricted audit storage holds source evidence, financial decisions and revisions
separately; access is authenticated and scoped, with customer exports excluding
costs, margins, internal notes and approver details. Demo data retention is seven
days after the demo, then delete cases, exports and source text; preserve only
aggregate metrics. Secrets live server-side in environment/secret storage.

## Budget and ownership

Live model calls default OFF. Available shared balance is UNVERIFIED, not zero
and not an assumed allocation. A budget owner must record balance, currency,
verification date and authorized allocation privately before enabling calls.
Do not commit billing screenshots, credentials or account identifiers.

Once funded, demo hard limits are 100 provider attempts per Singapore calendar
day, USD 1.00 total model spend/day, and USD 0.02 reserved maximum per attempt.
Use whichever limit binds first. Include failures/retries and in-flight calls in
atomic counters; maximum three attempts per case, each at most 4,000 input and
1,000 output tokens. Require verified per-model prices to reserve worst-case
cost before dispatch. Unknown pricing or insufficient reservation blocks calls.
Counters persist across restarts. No automatic cap increase. Hosting is separate:
local-only default, no paid provisioning authorized by this contract.

| Workstream | Deliverable | Accountable person |
| --- | --- | --- |
| Product/data | Confirm demo contract and source records | Unassigned; user to nominate |
| Agent/evaluation | Extraction, retrieval and golden-set report | Unassigned; user to nominate |
| Backend/cloud | Calculation, workflow, access and budget enforcement | Unassigned; user to nominate |
| Experience/QA | Six screens, PDF reconciliation and rehearsal | Unassigned; user to nominate |
| Budget | Verify balance and authorize model allocation | Unassigned; user to nominate |

Codex authored this demo contract under delegated design authority; it has not
assigned fictional people or verified the shared account. Implementation can
start locally with deterministic fixtures. Team kickoff and paid execution still
depend on those explicit human inputs.

## Acceptance and demo

`golden-cases.json` contains 25 synthetic cases with independent expected outcomes.
They are a frozen acceptance specification, not results from a working application
and not validated historical SME enquiries. `wireframes.md` defines all six views.

Happy path: Acme requests 50 C-curve 16A single-pole MCBs and 20 ABS boxes,
both from stock. Expected subtotal SGD 1,712.50, GST 154.13, total 1,866.63.
Exception 1: omit box material, clarify ABS, resume same case as a new revision.
Exception 2: request 80 LED panels with 20% extra discount, expose later stock,
obtain split-delivery consent and Finance approval before final review.

Release gate for the eventual demo application: all 25 case assertions pass;
100% exact commercial arithmetic and routing; no unsupported facts or sends;
all quoted values traceable; all six screens usable. Report extraction coverage
separately from match precision, including abstentions. Do not report fixture
consistency checks as application evaluation or measured business savings.
