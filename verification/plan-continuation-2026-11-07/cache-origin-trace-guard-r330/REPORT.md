Delivered a prospective diagnostic correction in R330 only. An installed tracer
now keeps control: the wrapper calls the original callable immediately, without
calling `settrace`, changing frame tracing flags, inspecting its errors, or
emitting diagnostics. With no tracer installed, the R314 diagnostic runs and
restores exactly `None` after return or unwind. The sole change from R314 is
the two-line `previous_trace is not None` early return.

`diagnostic.patch` applies to exactly these canonical files; neither was modified:

| File under `cache-refusal-cleanup-r8/` | Before SHA-256 | Prospective after SHA-256 |
| --- | --- | --- |
| `test_original.py` (2,372 → 4,052 bytes) | `9c82168832d97d006a7c99c084e8a5973a392a66c5e59ad388804a503a2ce77b` | `338ccbc6842bb02286cbfe206842120cc071f37a76205e6970bbb92a4212c404` |
| `sources.json` (3,160 bytes in both images) | `19af15d0fcb485957e2cb459c2a654e07f34f71ee52163f01a5336b17b09ec9b` | `b203fb9baa8ce322a29ef1b8ff6d15ae4de3057f4ddebb01aff59c8dab1e7d28` |

The source map retains all 20 members, changing only the test's bytes/hash row
and the tree digest from
`236f014f315b6e4b1f439fd6a2dad2a4121063507b1861ac5b0a2129faa1613b`
to `6d86513b0763799b7960814152d1f8b0f014b56d300d11edcd41c94580596333`.
The map uses its existing indented JSON plus newline encoding. Exact before/after
files and `prospective-bindings.json` accompany the patch.

Twelve inert tests pass in normal Python and an actual `-O` interpreter
(`sys.flags.optimize == 1`, `__debug__ == False`), using Python 3.14.8 / Clang
21.0.0. Only the AST-extracted helper runs, against in-process fake controls.
The canonical module, original suite, custody adapter and product runner are
never imported or executed. The active audit hook observed no filesystem,
process or socket operations during wrapper/control execution.

The tests prove return/error identity, first PermissionError coordinates,
bounded metadata without hostile exception getters, cleanup before emission,
restoration after normal/error/output-failure paths, and disabled diagnostic
line/opcode events. Existing global and local tracers actually receive control
events and the unchanged primary exception, with zero explicit `settrace`
calls. A throwing tracer preserves the same exception object and cleanup/event
sequence for direct and wrapped calls. CPython clears a throwing tracer itself;
the wrapper leaves that interpreter behavior intact.

The first normal run passed 11/12 tests and exposed a harness assumption:
CPython's automatic trace clearing emits a `sys.settrace` audit event. The
initial stderr/JSON are retained as `inert-normal.initial.*`. The corrected
harness separately records explicit API calls and compares the throwing-tracer
case against a direct call. No diagnostic code changed in response.

Reproduce from the repository root, with all outputs remaining here:

```text
python3 -B verification/plan-continuation-2026-11-07/cache-origin-trace-guard-r330/prepare.py
python3 -B verification/plan-continuation-2026-11-07/cache-origin-trace-guard-r330/test_inert.py
python3 -B -O verification/plan-continuation-2026-11-07/cache-origin-trace-guard-r330/test_inert.py
python3 -B verification/plan-continuation-2026-11-07/cache-origin-trace-guard-r330/adoption_guard.py
```

`prepare.py` only constructs files in R330. The compact read-only adoption
guard checks exact canonical preimages, afterimages, the two-file diff, and
the single-member map update. Removing just the helper and focal assignment
restores the entire original module AST, including all assertions. The two
static 36-control source files retain their original bytes/hashes; no original
control ran. After root separately applies the patch, use the same guard with
`--installed` to check exact canonical afterimages. Its pass is source evidence,
not runtime or CI acceptance. `prepare.py` requires the original preimages and
should not be rerun after adoption.

Keep source116 and live caller bindings unchanged. The canonical
`source_inputs()` selection excludes both verification paths; its selected
scripts and profile are unchanged. No full inventory was traversed or
remeasured, and no new source116 digest/count is claimed. The unchanged R8
`adopt_fixture.verify()` reads `sources.json` dynamically. The unchanged workflow
already invokes this wrapper in both modes and preserves stderr. No workflow,
caller, generalized controller or product-runner edit is needed.

`control-seal.json`, `cache-r8-acceptance.json`, the historical
`cache-r8-root-integration/verify_installed.py` and
`cache-r8-delivery/deliver.py` retain their original hashes and old pins/verdicts.
They do not approve this afterimage; do not rerun or rewrite those historical
records. `prospective-bindings.json` lists the exact unchanged references, and
the guard checks them without importing them. Root owns the fresh adoption
decision. This task commissions no further review.

The next named diagnostic is a future fresh ordinary `swift-cache-state-fixture`
CI run after root adoption. Existing normal stderr capture is
`verification/cache-fixture-shared-input-candidate-v2/logs/runner-controls.stderr`;
optimized capture is
`verification/plan-continuation-2026-11-07/cache-deadline-control-fix/runner-optimized.stderr`
if reached. The `cache-descendant-first-permission-error` marker should identify
the first actual Python PermissionError operation. With a tracer already
installed, diagnostic capture is intentionally skipped. Only a current-thread
first error is captured; timing overhead and hosted execution remain unqualified.
As in R314, a failing stderr sink can raise during emission after restoration;
successful diagnostic delivery is not claimed for that case.

This is not an engine fix or proof of a historical EPERM cause. All historical
failures, custody/process/scratch holds and final acceptance gates remain in
force. No root Git command, remote operation, real descendant, device operation,
held resource inspection, compiler or CI run occurred. Source identities are
exact relevant file digests; no current Git revision is asserted. AGENTS.md and
product-plan sections 24.5/25.3 were read. The implementation ran as Sol 6.1 at
xhigh, standard speed, alongside independently owned work; no child was launched.
