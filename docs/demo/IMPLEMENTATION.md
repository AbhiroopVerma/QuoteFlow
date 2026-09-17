# Local demo implementation plan

Goal: turn the approved demo contract into a usable local quotation workflow.

Architecture: Python HTTP API, SQLite case revisions, Decimal pricing, bounded
catalogue parser, static HTML/CSS/JavaScript interface. ReportLab generates PDFs
from server-calculated values. No model calls, uploads or external sends.

This first build is a single-user localhost sandbox, not production identity or
role-based access. Commercial exceptions are held for approval, never simulated
as genuine manager/Finance decisions. The UI labels the frozen fixture date and
offline mode. Fixtures are synthetic; storage is local and gitignored.

1. Write failing domain tests for golden monetary cases, parsing, clarification,
   stock consent, revision checks and customer-only exports.
   Run `python3 -m unittest discover -s app/tests -v` before implementation.
2. Implement `app/domain.py` for deterministic catalogue extraction, validation,
   pricing and exception detection. Use existing JSON fixture sources.
3. Implement `app/server.py` with SQLite transactions, bounded JSON requests,
   same-origin mutation checks, revision concurrency, local session cookie,
   sanitized error responses and a customer-safe quote document.
4. Build `app/static/` with inbox, enquiry modal, source/line resolution view,
   prices, stock acceptance, preview, PDF/email export and measured dashboard.
   Browser controls call server endpoints; no browser monetary calculations.
5. Test HTTP workflow, stale writes, uploads, exports and PDF text. Exercise the
   browser on desktop and mobile, including happy and ambiguous paths.
6. Document run instructions and limits, launch localhost, commit and push the
   working branch. No paid deployment or paid AI is part of this implementation.

Completion means the scoped end-to-end flow works. It does not mean the full
production proposal, semantic AI matching, authentication or all 25 end-to-end
golden cases have been implemented.
