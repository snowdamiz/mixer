# Active payload observation

Verification-only public API consumer of candidate5's frozen production/SDK
sources. The original tiny Wasm fixture enqueues eight storage gets in one
successful turn and polls eight separately stored guest wrappers. A concrete
AppPrivateKeyValueStore is seeded through its public API with49,152 binary bytes
(65,536 base64 bytes). All eight guest outcomes must preserve the entire value;
then exactly eight exit acknowledgements and drain must finish.

The LEB/section encoder is adapted from this lane's independently authored
`Tests/MixerExperimentalCapabilityRuntimeTests/GuestProgram.swift`; no engine or
third-party fixture builder is used. The fixture reserves32 initial memory pages
and131,072 bytes per response, within the existing ceilings. No production hook,
replacement adapter or SDK edit is used.

`python3 -B experimental-capability-runtime/verification/observe-active.py --name <fresh-name>`
exports the immutable candidate5 input manifest plus these observer sources into
ignored scratch, builds debug/release public consumers against the same pinned
host archive, runs each twice, and records source/binary/log hashes and commands.
An explicit `--base-receipt` can select a preserved earlier frozen candidate.
Prior receipts remain unchanged. A serial one-millisecond sampler keeps only fixed
counters/maxima; it runs until the bounded eight-request attempt drains. This
process includes large response copying, both codec conversions, native poll
copies and the observer's own public read/decode verification.

The process-wide malloc-zone in-use/allocated samples and getrusage RSS high-water
are observations. Sample maxima are not exact transient-copy or per-codec peaks,
not complete allocation tracing, and not hard RSS bounds. Sampling and probe
validation perturb allocation/timing. Pump-boundary logical phase bytes/workers,
callback duration and measured batch overrun are reported separately. DTO/backing
capacity, runtime Task retirement and opaque framework/native allocations remain
outside logical counters. The allocator maximum-in-use statistic returned0 in
the idle candidate3 run; it was not evidence of zero peak usage, so this observer
uses maxima of actual sampled in-use values. No physical-device, no-OOM/no-abort,
allocator-recovery, activation or release claim follows.
