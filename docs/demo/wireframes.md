# Six demo screens

Low-fidelity layout decisions, not a running app. Desktop uses a persistent
48px navigation rail and a case header. Case views share source on the left,
working content in the middle and decisions on the right. At widths below 900px,
use a single column with Source / Work / Decisions tabs; keep the case header
and primary action visible. Tables scroll horizontally without hiding actions.

## 1 Inbox

```text
+------+----------------------------------------------------------+
| Nav  | QuoteFlow                      [New enquiry]   Account    |
|      +----------------------------------------------------------+
| Inbox| Status [All v]  Search [_________________]                |
| Cases| Case       Customer         Updated    Status      Owner  |
| Dash | Q-001      Acme Facilities  10:00      Clarify     Admin  |
|      | Q-002      Acme Facilities  09:50      Review      Admin  |
|      +----------------------------------------------------------+
|      | Selected: Q-001 | 4 requested lines | [Open case ->]      |
+------+----------------------------------------------------------+
```

New enquiry opens a modal with labelled customer, subject and multiline email
fields, character counter and Create/Cancel. No upload control. Empty inbox
offers New enquiry. Creation failure retains text and shows a retry action.
Potential duplicate opens the existing case or requires explicit new-case intent.

## 2 Resolve

```text
+------+----------------------------------------------------------+
| Nav  | Q-001  Acme  Revision 1  Needs clarification  [History]    |
|      +----------------+-------------------------+---------------+
|      | Original email | Requested lines         | Decisions     |
|      |                | Qty  UOM  Description   | Box material? |
|      | highlighted    | 20   EA   IP65 box      | ( ) ABS       |
|      | source phrase  |                         | ( ) Metal     |
|      |                | Candidate specification | [Confirm]     |
|      |                | ABS / Metal comparison  | Evidence      |
|      +----------------+-------------------------+---------------+
|      | [Back]                      [Continue to pricing] disabled|
+------+----------------------------------------------------------+
```

Line selection synchronizes source highlight and candidate comparison. Show
missing attributes beside confidence, not hidden in a tooltip. No matches,
malformed extraction and unavailable catalogue are distinct states. Continue
requires every line resolved. Confirmation records actor, source and revision.

## 3 Price

```text
+------+----------------------------------------------------------+
| Nav  | Q-001  Acme  Revision 2  Commercial evaluation             |
|      +----------------+-------------------------+---------------+
|      | Original email | SKU Qty Source Net Stock| Exceptions    |
|      |                | MCB 50 Gold   26.27 200 | None          |
|      |                | ABS 20 Gold   19.95 100 |               |
|      |                | Discount [0.00] %       | Source record |
|      |                | Margin / rule result    | Version/time  |
|      |                | Subtotal       1712.50  | [View source] |
|      |                | GST             154.13  |               |
|      |                | Total SGD      1866.63  |               |
|      +----------------+-------------------------+---------------+
|      | [Back]                             [Prepare draft]        |
+------+----------------------------------------------------------+
```

Costs and margins are internal only. Stock shortfalls show quantity/date options
and an explicit customer-consent field. Calculation loading disables progression;
invalid/stale sources block with a named reason. Any edit marks approvals invalid.

## 4 Approve

```text
+------+----------------------------------------------------------+
| Nav  | Q-003  Revision 3  Awaiting approval                       |
|      +--------------------------+-------------------------------+
|      | Requested change         | Approval timeline             |
|      | LED extra discount 20%   | Finance: pending              |
|      | Net 47.18; margin 9.92%  | Administrator: pending        |
|      | Effective discount 22.4% | Revision hash / request actor |
|      | Delivery consent recorded|                               |
|      +--------------------------+-------------------------------+
|      | Decision reason [____________________________________]  |
|      | [Request revision]       [Reject]          [Approve]     |
+------+----------------------------------------------------------+
```

Actions appear only for authorized actors and are checked again on the server.
Self-approval and stale revision return explicit errors. Rejection requires a
reason; approval records the exact version. Pending roles remain visible even
when the current actor cannot act. Final review is separate from Finance approval.

## 5 Preview

```text
+------+----------------------------------------------------------+
| Nav  | Q-001  Revision 2  Human review                            |
|      +----------------------------------+-----------------------+
|      | Quotation                        | Review checks         |
|      | QuoteFlow Demo Supplies Pte Ltd   | Customer confirmed    |
|      | Acme Facilities Pte Ltd           | Recipient confirmed   |
|      | Product / quantity / price        | Sources current       |
|      | Subtotal / GST / SGD total        | Approvals valid       |
|      | Delivery / Net 30 / validity      | Document reconciled   |
|      |                                  | Email draft           |
|      +----------------------------------+-----------------------+
|      | [Back]       [Download PDF]           [Mark reviewed]     |
+------+----------------------------------------------------------+
```

Draft PDF has a visible DRAFT marker until review. Downloaded customer content
never includes costs or margins. Missing checks block Mark reviewed. Hash or
value mismatch blocks export and offers regeneration. Reviewed is the terminal
demo state; there is no Send button. Source revalidation failure preserves draft.

## 6 Dashboard

```text
+------+----------------------------------------------------------+
| Nav  | Dashboard                 Date range [Demo session v]    |
|      +----------------------------------------------------------+
|      | Received 12    Needs clarification 3    Reviewed 4        |
|      | Median preparation: -- (insufficient completed cases)    |
|      +----------------------------------------------------------+
|      | Queue by state                | Exceptions by cause      |
|      | Needs clarification  ### 3    | Missing attribute  ### 3 |
|      | Awaiting approval    ##  2    | Stock shortfall     ## 2 |
|      +----------------------------------------------------------+
|      | Evaluation: not run    Dataset: demo-v1 / 25 cases        |
|      | Model calls today: 0/100  Spend: $0/$1  Live calls: OFF    |
+------+----------------------------------------------------------+
```

Numbers above illustrate layout, not measured results. Runtime starts at zero
with unavailable metrics shown as unavailable. Clicking a queue count filters
Inbox. Evaluation distinguishes passed, failed and not run; replay events are
labelled and excluded from live performance metrics. Budget unverified is visible.
