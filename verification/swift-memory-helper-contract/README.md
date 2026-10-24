This frozen packet is a private Load/Store contract/type/layout prerequisite.
Run `python3 -B verification/swift-memory-helper-contract/verify.py` for offline
integrity, actual-output parsing, canonical role replay and source-expansion
identity. It runs no Cargo command, interpreter or device.

`candidate-source.tar.gz` is the exact complete compiling source overlay; the
manifest SHA-256 is its source authority. `candidate.patch` is review material
against the exact accepted baseline archive. Product and metadata sources are
separate. The metadata source adds only size/offset printers and uncalled method
pointer type assignments; its one selected unit test executes no guest opcode.
All metadata executables are bound by hash before owned scratch cleanup.

The scripts retain the actual original collection recipe and command receipts.
They intentionally refuse an existing command-output directory. To reproduce a
fresh build, extract a source archive into a new owned directory and run the
frozen command argv with a new owned CARGO_TARGET_DIR and the recorded toolchain.
For fresh layout collection use the separately archived metadata source; the
production/unit commands and exact outputs are in commands/layout-*.
`proposal.rs` is the authored body template before generated positive positions;
it is not a second executable implementation or the final source authority.

`historical-attempts.json` and `historical-before-promoted-constants/` identify
excluded/superseded observations. In particular, an expansion with source drift
and a finalization attempted while metadata receipts were still being collected
supply no acceptance evidence. Stable-source reruns and final archive-only
collection supply the current packet. All output compression is lossless and
retains the raw-output SHA-256 in its command receipt.

The next behavior lane must implement and execute every exact test in
`acceptance-matrix.json`. `acceptance_matrix.py --run` requires explicit source
binding, an owned target directory, every exact test identity and successful
non-ignored execution, with bounded command timeouts. Those tests do not exist
in this packet and every behavior case remains pending. No Root/independent
contract acceptance is implied by the packet's self-verification.
