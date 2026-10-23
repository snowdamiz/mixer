# Native capability boundary review preparation

This directory contains independently authored public-C adversarial tests and tiny
original Wasm fixture builders. The first frozen candidate passed actual debug and
release public-C execution; those receipts and exact review inputs are preserved
in `attempt-1/`. A default-feature Clippy-only correction changed the source freeze,
so final replay and the owner matrix audit are pending refreshed archive pins.
The mutable SDK/VM is never an implementation edit target for this lane.

The public client is prepared to check shared sixteen-slot capacity across old/new
session families, retained closed dispatches, real slot generation reuse, duplicate
acknowledgement before/after mailbox release, cancellation controls, interpreter
trap cleanup, memory snapshots/bounds, unaligned structures, report-inclusive
alias rejection with unchanged sentinels, numeric pointer overflow, null reports,
old profile rejection and 48 take/close plus 48 ack/close races. After racing, it
fills and releases all sixteen slots to detect leaked capacity. No native I/O is
started; trusted completion JSON is posted as an opaque installed-caller value.

Pre-freeze inspection identified ambiguous after-ack versus existing-terminal
precedence and a missing expire unwind guard. The owners corrected the header to
preserve the frozen mailbox precedence and added published-session unwind guards.
The client follows the corrected contract: an existing unconsumed terminal yields
kind1 even after exit; an early exit without a terminal rejects post/deadline.

A later receipt must pin the frozen source/header/archive, fixture/test bytes,
compiler/link commands, outputs and exact scope. Public stress races do not replace
internal barrier/unwind/poison/destructor tests needed to prove precise registry
linearization. No physical-device, release, Swift bridge, C-unwind-at-every-injected-
point, OOM, operational or GA qualification follows from test preparation.
