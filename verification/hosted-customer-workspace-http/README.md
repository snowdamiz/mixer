# Bounded customer workspace HTTP evidence

`run.py --source-revision ROOT_SUPPLIED_REVISION` creates the next immutable
`run-N` with explicit ordinary source copies/hashes, exact commands, pinned
general dependency versions and BEAM hashes, compiler/test output and cleanup.
It runs only the workspace transport tests and existing artifact transport tests.
It does not run `hosted/scripts/test-local.py`, load the application ebin, compile
the full application, or discover product sources recursively.

`transport_defaults.ex` is a standalone collector-only declaration fixture. Its
default facade functions raise if reached. Real product tests do not import it;
the transport tests supply their own trusted facade, while production-router
missing-bearer cases must halt in BearerIdentity. These declarations provide no
domain/runtime qualification. Root's separate integration lane uses the actual
default verifier, backend and Repo.

`run-3` is passing: 22 workspace and 32 existing artifact tests, formatting pass,
zero cold compile/runtime warnings, no source drift and scratch cleanup. Earlier
failed runs are retained and explained in the producer document. No server,
database, native, capture, provider or production process is started here.
