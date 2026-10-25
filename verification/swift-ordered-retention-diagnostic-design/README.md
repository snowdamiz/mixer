# Ordered-retention diagnostic design evidence

Design only; no Rust or target execution is selected. The proposed capped,
baseline-policy stream and pending acceptance gates are in
`docs/swift-ordered-retention-diagnostic-design.md`.

Run the synthetic controls without creating a new receipt:

```sh
python3 -B verification/swift-ordered-retention-diagnostic-design/verify.py
```

`verify.py` rehashes this packet/document and only the 132 named live VM files,
then executes the finite Python codec/state controls. It never imports product
code or prior producer scripts, restores sources, runs Rust/guests/native tests,
scans processes, or writes temporary/build files. Root metadata is historical
context in command receipts and is not required to stay frozen.

`run_checks.py` is the finite receipt producer. Its ordered attempt directories
retain exact selected input hashes, own source hashes, Python tool/platform,
argv/environment, stdout/stderr, exit and unchanged named VM closure. Attempt 1
passes the initial 16 controls; attempt 2 passes 17 after adding the distinction
between slot removal and drop/refund completion. Later receipts bind final
controls. The finalization correction adds six finite model methods including
all 140 interleavings of two callback chains and End; the strict cap-cardinality
control adds one wire method. The combined current suite has 25 methods.
There were no failing synthetic test attempts. Earlier read-only
path-guess errors are preserved in `exploration-failures.json`; that file is an
authored concise record, not a raw reconstructed transcript. Earlier command
hashes do not claim a complete source archive for every intermediate draft.

`codec_model.py` is a finite synthetic model, not the Rust writer/analyzer. Its
footer lifecycle fixture is construction/preconsumption/final-consumption only;
it does not implement full production lifecycle, closed event-specific payloads,
count-plan/work replay, syscall/fault injection or observer memory measurements.
Those remain explicit implementation gates. Its synthetic event lists and
Python dicts are bounded fixture allocations and must not be copied into the
future streaming implementation.

The original first freeze is retained byte-for-byte as 22 safe regular archive
members (20 sealed inputs plus its seal and sidecar), with original seal
`b97621fe4a547112baa49052009ab1c78d0b39b4de04d95b596c663399b88db8`.
`history/first-freeze-preservation.json` records its exact archive length/hash.
No archive was extracted or executed. Finalization/custody corrections preserve
the initial source and attempt receipts; full Rust atomic correctness,
single-thread dispatch/quiescence and layout remain pending.

The maximum proposed ordinary stream is 512 MiB plus 1,024 framing bytes; no such
file is generated here. One custody copy allows two stream files, totaling
1,073,743,872 bytes plus a combined <=8,192-byte sidecar, before distinct bounded
original output/result/source/binary receipts. Host copy storage has its own
65,536-byte buffer/two-descriptor and <=131,072-byte logical inventory gate;
it is separate from live observer storage. Source-policy/work counts, observer operation bounds,
typed value sizes and physical performance/memory are distinct quantities.
Original CacheWork failure, all three policy rejections, production limits and
full product/GA requirements remain unchanged. No scratch source, compiler,
native instance or capture process was created; no cleanup deletion was needed.
