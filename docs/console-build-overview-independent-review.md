# Builds view independent review

The final captured Builds display slice passed seven independent controls, an
isolated application source typecheck, and an owned Vite production build on
Node 22.23.3. No unresolved findings remain within this source and host scope.
The [receipt](../verification/console-build-overview-independent-review/receipt.json)
contains commands, runtime/dependency versions, executable/output hashes, exact
source closure, and cleanup. Root owns browser and integration acceptance.

## Finding and correction

The initial display validator used 256 JavaScript code units for identity text,
trimmed whitespace, and counted source references by code units. The accepted
hosted lifecycle uses 128 UTF-8 bytes for organization/project/application/build
IDs and 1024 bytes for source references, with valid Unicode and Elixir
`String.printable?` semantics. The mismatch could display a successful identity
that the hosted constructor could not accept, or reject a valid printable label.

The producer corrected the validator before this review ran. Independent
controls accept exact byte boundaries and backend-printable whitespace/control
characters, preserve supplied text, and reject overlong ASCII/multibyte text,
lone surrogates, and representative nonprintable code points. The reviewed
domain SHA-256 is
`3b57454505da750c70cff73b808053a62af61bec04ac5aabaffcc3d2d476abed`.

## Observed checks

- Reversed reports preserve independent iOS/Android build IDs and immutable
  digests. A failed platform remains visible beside success; there is no overall
  success status or action control.
- Every common-scope or full immutable identity substitution, duplicate target
  or report, unexpected field/platform, and unsupported status rejects the
  entire overview without retaining outcomes.
- All eight lifecycle states preserve `workerCompletionPending` exactly.
  Cancelling and reconciling retain explicit worker uncertainty. Timed-out
  attempts can retain a late non-infrastructure failure, as the lifecycle does.
- Zero or partial reports preserve all selected expected identities as explicit
  unreported cards. Single-platform selections work. Loading, unavailable, and
  invalid wrappers expose no prior outcomes in compiled Solid SSR output.
- Returned nested snapshots are copied and frozen. A standard HTML parser
  confirms hostile labels create no executable tags, links, handlers, or raw
  markup in the actual compiled Solid component. Immutable digests sit inside
  closed native details elements.
- The isolated strict application source typecheck and Vite build pass. The
  production bundle contains unavailable-state copy and excludes synthetic
  Builds preview data/chunks. Website logo/favicon bytes and effective theme
  tokens match exactly.

The review source-tree digest is
`ec89b48fe6ae99481dbe7e88cc158d6870685a3c49b3b895a8a8c4d8e7821cd8`.
It covers the captured console, accepted hosted lifecycle, product instructions,
and website brand inputs, so it has a broader closure than the producer digest.
No captured input changed during execution. The temporary dependency-resolution
symlink was removed; shared dependencies were not modified. No server, browser,
native instance, network operation, dependency installation, or Git operation
was used by this review.

## Limits

This packet executes SSR and a local production build. Reactive browser
transitions, responsive layout, focus, screen-reader behavior, contrast, and
interactive disclosure remain in root's browser scope. The producer's full
console suite was not replayed here. Existing `skipLibCheck=true` leaves
dependency declarations outside application source typechecking.

The view model remains internal. A future authorized Phoenix adapter must join
the exact selected spec and status. This review establishes no customer
API/authentication/authorization integration, real worker or hosted operation,
signing, distribution, native/device evidence, FieldLog qualification, or GA
gate acceptance.

## Responsive CSS supplement

Root subsequently constrained the development preview label to `max-width: 100%`
and allowed its select to shrink with `min-width: 0; flex: 1` after observing
control overflow at 320px. The [separate CSS supplement](../verification/console-build-overview-independent-review/css-supplement.json)
verifies the exact two-declaration change and confirms all other 27 captured
inputs, including domain/component/App sources and website branding, are
unchanged. The original receipt and snapshot remain intact. Fresh browser
containment and production-build checks belong to root; this supplement only
binds the source comparison.
