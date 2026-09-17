# QuoteFlow local sandbox

## Run

Follow the [step-by-step localhost setup](../README.md#run-the-quoteflow-demo)
for prerequisites, the correct Git branch, macOS/Linux and Windows commands,
starting/stopping the server, and troubleshooting. No remote assets, model
calls, credentials or email service are used at runtime.

## Available workflow

- Create an enquiry with an explicit synthetic Acme/SGD/Jurong confirmation.
- Start with the three built-in example inputs, or paste your own text.
- Exact SKUs and complete known catalogue descriptions resolve deterministically.
  Ambiguous material/specifications and unknown lines remain for human correction.
- Confirm/edit each SKU, quantity, UOM and discretionary discount. Confirmation
  calculates prices, totals and commercial triggers on the server using Decimal.
- Record explicit split-delivery consent when inbound stock is required.
- Preview and export a customer-only draft PDF or text email. Final review is
  blocked until line questions, delivery and commercial rules pass.
- Standard quotes can be marked reviewed. Manager/Finance exceptions stay on
  hold: the local operator is not impersonated as an authorized approver.
- Filter/search the queue, inspect revision events and delete local cases.
- Inspect real local case counts in Overview. No fabricated performance metrics.

## Boundaries

This implements the first end-to-end slice, not every production proposal feature.
The business clock, stock and effective dates remain frozen to the fixture date
17 September 2026. The user confirms the requested customer, currency, site and
19 September delivery context. The source text is retained, but extraction is a
limited catalogue grammar, not general email understanding or semantic AI search.
Always inspect lines before confirming. Date/customer recognition from prose,
model confidence, live source freshness and production adapters are not implemented.

The server recalculates all money; browser-supplied financial totals and approval
fields are ignored/rejected. All reviewed-case edits invalidate final review.
Expected revision numbers reject stale writes. The displayed checksum represents
the structured customer projection, not the PDF bytes or a digital signature.
PDF and email are generated from that same allowlisted projection. Draft export
is allowed while commercial approval is pending and remains marked as a draft.
Unknown products and unaccepted delivery prevent export.

Local sessions use an HttpOnly SameSite cookie plus Origin/Host checks, request
size limits and a restrictive content policy. This is NOT multi-user identity,
role-based authorization, production audit immutability, encryption at rest,
idempotent network retry handling or a billing enforcement service. Browser
double submission is disabled, but retrying a failed create may create a second
case; inspect the queue before retrying. File uploads are rejected. The request
logger is disabled; raw enquiry content is never emitted to operational logs.

SQLite stores case inputs and revision event metadata at `app/data/cases.db`,
which is gitignored. It does not retain complete historical input snapshots.
Delete cases using the trash control after the demo. Automatic seven-day expiry
is not implemented; the local operator owns deletion. Stop the server before
removing a local database. No sensitive real customer information belongs here.

## Verification

```bash
python -m unittest discover -s app/tests -v
python docs/demo/verify_fixtures.py
node --check app/static/app.js
```

The domain tests recompute the 13 monetary golden expectations using the actual
app engine, plus parser and validation probes. HTTP tests exercise standard
review/export, concurrency conflicts, upload rejection, cross-origin checks and
approval holds. This is not a report that all 25 golden enquiries passed through
the parser and workflow; the unimplemented golden scenarios remain future work.

For browser checks, install Playwright in your test environment and run, with
the app server already running on port 8765:

```bash
node app/tests/browser.cjs
```

Set `PLAYWRIGHT_MODULE` to an installed Playwright package path if it is not on
the normal module path. `BROWSER_CHANNEL=chrome` uses installed Google Chrome;
otherwise install Playwright Chromium. Tests run happy path, clarification and
approval-hold flows at desktop/mobile sizes, download a PDF, check page overflow
and JavaScript errors, then delete only the cases they created. Screenshots and
the downloaded PDF go to gitignored `work/browser/`.
