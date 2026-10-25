# Customer workspace client

The read-only SolidJS console transport calls the actual workspace API contract:
`GET /v3/orgs` and `GET /v3/projects?organization_id=...`. Full valid workspace
identifiers are encoded once in the query, including dots, slashes, spaces,
Unicode and literal percent/plus characters. The shared domain parser validates
and freezes returned organization/project pages and enforces exact project scope.

Trusted application configuration supplies one HTTPS origin and a function that
resolves the current in-memory session token for every request. The client does
not persist tokens or choose a login provider. Requests omit cookies, reject
redirects, bypass browser caches, suppress referrers and send bearer tokens only
in the Authorization header. Explicit development configuration permits HTTP
only for loopback hosts.

One bounded deadline covers session resolution, fetch and streaming. Caller
cancellation prevents a late session token from starting a fetch. Response reads
are limited to 256 KiB and 4,096 chunks, including empty chunks. Only strict UTF-8
JSON and validated closed pages are accepted. Errors expose fixed categories;
provider text, raw response bodies and URLs are never copied into errors.

Twelve focused tests exercise the actual TypeScript-emitted client, including a
real disposable Node HTTP listener, exact wire query/header behavior, foreign
scope rejection, token rotation, timeout/cancellation and malformed responses.
The complete console suite and production build are recorded separately in
`verification/console-workspace-client`. The test closes the listener and removes
its emitted JavaScript directory on success and compiler failure.

This is transport implementation, not a completed login or connected product
screen. Root App/session/selection composition, actual browser interaction,
accessibility runtime and deployment remain pending. The production bundle may
tree-shake unreferenced code; focused tests compile and execute the client
explicitly. No new dependency, screen capture, native runtime, provider account,
customer or GA qualification is implied.
