# Application structure and workflow

Refactor on `codex/working-demo`, preserving the approval work already in progress.

Target boundaries:
- `app/frontend/`: browser markup, styles and JavaScript; no SQL or pricing math.
- `app/backend/`: HTTP interface, quotation rules, approvals and document output.
- `app/database/`: schema, initialization and repository operations; no HTTP/UI.
- `app/tests/`: pricing, workflow, persistence, HTTP and browser checks.
- `app/server.py`: stable launch entry point, retaining `python -m app.server`.
- `app/data/cases.db`: existing ignored local runtime data, retained in place.

First add repository rollback/snapshot tests and specification-renderer tests.
Move existing modules with updated imports, extract SQL behind repository
functions and run the existing request/domain/workflow tests. Keep frontend
requests and backend route names stable. Update README commands and browser tests.

Product specifications remain structured catalogue facts. Icons are secondary
to readable values and have descriptive labels/tooltips. Use Lucide for amperage,
poles, curve, cable dimensions, lighting power/temperature and enclosure material.
Never infer an unstated rating, certification or dimension from an icon.

Validate syntax, existing behavior, repository tests and DOM-independent icon
rendering locally. Live HTTP/browser checks and push still require workspace
approval availability; do not claim those passed without running them.
