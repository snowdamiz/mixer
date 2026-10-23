# Shared Swift/WASI control boundary

`isolated-2/receipt.json` binds committed020f909 plus exactly four root-owned
helper files. Debug and Release each pass77 all-feature library tests and15
original standalone WASI/allocation tests. Library/binary Clippy and formatting
pass. The snapshot excludes the concurrently implemented accounted WASI wrapper.

The shared control now accepts the real WASI usage at check/host-entry boundaries,
so the immutable first failure retains that observation without duplicate counters.
A borrowed sealed ticket checks component/control pairing before dispatch without
admitting or refunding storage. Existing check/host methods preserve None behavior.
The unit-only allocator adds thread-local zero-based fault injection across
allocation/zeroed/reallocation requests; failed realloc preserves its old buffer.

`isolated-1` remains failed: its new direct std::alloc selfcheck aborted under
Release optimization. The localized diagnostic also failed. The repaired test
uses an opaque allocator call and handles unexpected realloc success without
reading or freeing a stale pointer. The allocator implementation did not change
between these attempts. No product execution, physical device or GA gate is
qualified by this helper-only check. Complete wrapper composition has its own
subsequent source-bound evidence and independent review.
