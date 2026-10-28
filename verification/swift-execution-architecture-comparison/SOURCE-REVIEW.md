# Candidate source boundary

Root selected the original 256-entry algorithm and the dense-index candidate
under identical finite calibration bounds. This directory is the complete
implementation ownership boundary. It contains no new external dependency.

`candidate.py` transforms only the frozen, hashed v1 source archive. The control
and candidate share the exact original guest harness, full input, eleven-field
oracle, policy values, prefix observer, frozen IR/token tests and original
instruction/bulk metering. The candidate's additional algorithm edits are confined
to the copied generic cache hooks, copied Swift cache and copied Swift cache tests.
No canonical engine or frozen evidence packet is edited.

The resident map has 80,000 u16 cells: 160,000 bytes. The original complete
metadata validator caps definitions at `80,000 - imports.len()`, so absolute
validated IDs fit; the existing pin descriptor lookup rejects imports before
map access. Zero is absent and values 1 through 256 identify actual resident
slots. Every hit verifies actual resident identity. Miss and structural-mutation
paths audit every actual slot's reverse association, preventing orphaned map
cells or duplicate resident publication. The old full-chain algorithm's cycle
state has no counterpart in the dense representation; merely trusting an encoded
slot or skipping actual-key checks would be a different, rejected implementation.

The free-pin map is an eight-byte scalar in the actual cache owner and partial
constructor owner. Its live borrow is part of SwiftScratch. Acquisition checks
mask bounds and live-count agreement, selects the lowest available bit, verifies
the actual PinRecord, and precharges its publication. Exclusive owner borrowing
keeps that checked bit stable while cache construction occurs. Record and bit
publish together only after successful pinning. Existing token owner, slot,
nonce and resident-pin checks still precede view/release. Release validates its
mask bit without polling an already exhausted work/cancellation budget, then
updates record and bit together. No error path can publish a pin bit alone.

`DenseIndexInventory` and `DensePinInventory` conservatively cover the new named
locals, borrows and return shapes in triplicate in permanent, construction and
operation envelopes. Existing inventories remain. Actual owner, partial owner,
scratch and transfer `size_of` calculations also include their added fields.
The index payload is admitted in the original header before allocation and
released only after index destruction. All 80,000 initialization writes are
charged before one bounded 160KB exact-reserved zero-fill, with stop checks before
and after it. There is no constructor allocation in the hot hit path.

Actual compiled layouts and the simultaneous conservative envelope are still
pending. The driver must prepare **both** arms, including their finite geometry
and zero-cleanup receipts, before counting or spawning either full attempt.
The prior envelope's 1,647,194-byte margin and source arithmetic are not a
substitute for this executable admission gate. New instrumentation is diagnostic
overhead: at most three external stderr records and 8KiB of prefix output,
separate from product reservations and the eleven-field oracle. Its code is
byte-identical in both arms. Prefix counts are charged instructions before the
selected instruction's effect; equal counts do not promise identical host
entropy or guest paths. Cursor and cumulative metrics are preserved to expose
that limitation.

Six candidate finite tests cover actual owner retention/eviction and all 64 pins,
lowest/highest keys and import rejection, map corruption and duplicate prevention,
mask corruption and stale/foreign/reused tokens, every replacement/hit work and
cancellation prefix, constructor allocation/capacity/work/cancellation boundaries,
header lifetimes, the compiled conservative full-owner envelope and unchanged
frozen-mode IR/token test bodies. These tests are prepared but have not run.

The offline source generator and Python runner tests establish source/decision
contracts only. They do not establish Rust syntax/type correctness, resource
admission, VM parity, cleanup at runtime, performance, native readiness or GA.
The next selected runtime must preserve those pending boundaries explicitly.
