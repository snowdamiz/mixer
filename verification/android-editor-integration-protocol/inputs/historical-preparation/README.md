# Android editor integration preparation

This frozen preparation checks integration prerequisites for the corrected
candidate sealed by `4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3`.
No canonical product, CLI source profile, historical callback map or native
runtime was changed. This is not candidate acceptance.

The candidate changes three existing Java subjects and adds the direct
`NativeEditorConnectionV2` subject. All other copied production subjects still
match canonical bytes. See `prospective-product-map.json`. A later accepted
integration will require an explicit new source-pair profile, export roster,
host/cross-compiler source lists and generated-project rejection tests.

The existing owner orchestration suite passes 222 cases / 1,180 assertions with
the exact candidate coordinator. Its controlled renderer leaf adds only
`editorDisposalBusyV2() = false`; this suite does not model editor busy behavior.
The successful run is `closure-A-corrected`.

The existing concrete renderer suite compiles against the complete candidate and
its controlled host leaves, but does not pass. The retained runs expose these
integration requirements:

- `closure-B-corrected` assumes the initial cursor is at the end of the text.
  The new leaf follows the pinned default movement method's initial zero
  selection. An append test must explicitly place its cursor; it cannot change
  the platform model to force the expected value.
- `closure-B-explicitcursor` proves initial zero selection and establishes the
  append cursor. It also moves the now intentionally refused `sendKeyEvent`
  operation into existing no-native-call refusal assertions. It then fails the
  old close frame assertion because the mechanical probe's product allowlist
  omits the new direct adapter class.
- `closure-B-directprobe` adds that class to the copied probe. It then fails the
  old `beginBatchEdit` current-state case. The old test deliberately sets the
  actual product `record.changing` flag to suppress feature delivery; the new
  editor entry guard refuses that state. This test setup needs a reviewed
  replacement. It is not evidence that normal healthy beginBatchEdit fails.

The latter two runs explicitly omit the historical callback matrix and cannot
count as matrix acceptance. The original map contains 189 sites; unchanged-line
matching finds 171 possible anchors and 18 changed/removed anchors.
`barrier-map-migration-inventory.json` is an inventory only: it neither validates
those anchors nor covers new direct editor boundaries. A new exact source and
runtime callback review is still required.

The first two checker attempts failed before any compiler or product process
because this root-owned checker assumed a `files` seal key instead of the actual
`members` key. The authoring source and failure record are retained under
`authoring-failures`; those failures did not modify the candidate.

Every compiler/runtime invocation retains source snapshots, actual command,
tool identities, raw output, emitted classes and cleanup. A/B use JVM controlled
leaves only, with no native instance or capture query/start. All owned children
were reaped and scratch removed. The independent correction review separately
found the real previously-focused field compatibility gap; that verdict is not
replaced by these integration observations. Canonical integration, native
runtime, public V2 and GA remain pending.
