# Unchanged fixture library compilation

The selected preparation's illustrative non-test fixture library command used
`-Dwarnings`. Actual Rust 1.99 compilation reports inherited unused-assignment and
dead-code warnings in the unchanged closed fixture. That failed command and its
complete diagnostic output remain evidence; they are not a candidate pass.

For this isolated bridge only, select the existing accepted canonical runner's
non-test library policy: `rustc --edition=2021`, Debug or `-O`, explicit crate name,
`--crate-type=lib`, exact unchanged `source/library/analyzer.rs` closure and an
owned output. Do not add `-Dwarnings` or `-Awarnings`. Retain normal compiler
warnings in bounded output, and inventory their diagnostic kinds and source
paths. The canonical runner is
`verification/swift-cache-state-ci/check_cache_state.py`, SHA256
`e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b`.

This amendment changes neither fixture source nor its canonical CI runner. It
does not suppress diagnostics, relax the new adapter's own warning policy,
install tools, change caps or deadlines, run the full fixture command suite, or
qualify a real header/runtime. New bridge and adapter compilation retains its
selected strict warning policy. Unexpected errors or warnings in new source
still require diagnosis. Independent review must verify the exact compiler
arguments and unchanged fixture source closure in both modes.
