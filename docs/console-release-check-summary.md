# Console release-check summary

Product-plan section 17 requires the release screen to retain platform failures
instead of hiding them beneath a green group status. The first console domain
module implements that display rule independently of the pending Phoenix API
and SolidJS application. It adds no HTTP contract, route or privileged action.

The caller supplies the selected release revision, the explicit target-binary
list and the required check identifiers. Each reported result names one target,
one required check, its revision, and `passed`, `failed`, `pending` or `not_run`.
The module rejects malformed or duplicate identifiers, unsupported states and
unexpected target/check pairs. Missing results become `not_run`; results for a
different revision become `stale`. Every target/check pair remains visible.

The aggregate and each target use the same precedence: a current failure wins,
otherwise any pending, unrun, missing or stale result means `incomplete`, and
only a complete set of current passing results means `passed`. A stale passing
receipt cannot qualify a newer release. Historical failed results remain visible
as stale rows, without asserting they describe the current revision. There is no
input aggregate status to trust or override this computation.

This is a reported-check display model, not release authorization, cryptographic
receipt verification or permission evaluation. Phoenix must enforce those
boundaries. The later console adapter must receive the authoritative expected
target/check set and revision through its selected API contract; callers must
not infer requirements only from whichever results happen to arrive. No fixture
can qualify an integrated or deployed console gate.

The implementation has no added runtime dependency. TypeScript 5.9.3 is pinned
as a development dependency with its integrity and license recorded in
`console/THIRD_PARTY.yml`. Strict compiler checks pass. Node's built-in test runner
executes the TypeScript source using [type stripping](https://nodejs.org/api/typescript.html),
which is enabled by default starting in Node 22.18.0 and performs no type checking.
SolidJS/Vite/Router integration, user interaction, accessibility, Phoenix API
parity and Cloudflare deployment remain pending.

```sh
cd console
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm test
```
