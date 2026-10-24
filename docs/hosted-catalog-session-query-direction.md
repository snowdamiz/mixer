# Fixed catalog-session query qualification

Root approves a separately bound `pg_catalog`-qualified equivalent of the
original fresh-runtime-session query in the isolated two-repository catalog
inspector. The selected nine fields and their exact comparison remain unchanged.
Keep the original SQL literal as historical input and retain the precise query
delta; this is semantic equivalence to test, not byte identity to claim.

The runtime checkout has not set a local search path before this capture.
Therefore every catalog builtin function and explicit type reference in the
runtime session/backend checks, and in observer checks before its fixed local
search path, must be schema-qualified. Preserve SQL keywords such as current_user
and session_user as keywords. No session mutation or caller-selected SQL is added.
The original legacy/enforcement resources remain exact and execute inside the
observer's read-only repeatable-read transaction with `search_path=pg_catalog`.

Require a real hostile search-path/function-shadow fixture: the qualified query
must observe true builtin session/backend state and reject any mismatching role,
instead of accepting fabricated matching fields. This fixture uses only disposable
owned PostgreSQL resources. Retain actual outputs and any failed attempts.
The observer profile, connection ownership, deadlines, cleanup and review
requirements in `hosted-catalog-observer-direction.md` remain binding.
No live SQL, credentials, production startup or GA acceptance is authorized here.
