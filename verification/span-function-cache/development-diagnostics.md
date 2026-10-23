# Development diagnostic provenance

The initial `cargo check --offline --manifest-path vm/Cargo.toml --features
experimental-function-cache` found an untyped `oldest = None` selection variable
and a Rust 1.99 deprecation of `AtomicU64::fetch_update`. The implementation now
uses `Option<usize>` and the installed toolchain's `AtomicU64::try_update`.
The next feature check passed.

The first `cargo clippy --offline --manifest-path vm/Cargo.toml --features
experimental-function-cache --all-targets -- -D warnings` failed with 21 instances
of the following diagnostic (excerpt of the observed tool output):

```text
error: the `Err`-variant returned from this function is very large
  --> src/experimental/cache/decode.rs:10:50
   |
10 |     fn byte(&mut self, meter: &mut Meter<'_>) -> Result<u8, CacheFailure> {
   |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^ the `Err`-variant is at least 176 bytes
   |
   = help: try reducing the size of `experimental::cache::CacheFailure`, for example by boxing large elements or replacing it with `Box<experimental::cache::CacheFailure>`
```

The cache keeps bounded scalar usage diagnostics usable under allocator failure.
Boxing those diagnostics would violate that contract. A module-scoped
`#[allow(clippy::result_large_err)]` was therefore added with the explicit comment
`Static bounded diagnostic snapshots must remain usable after allocation failure.`
No other Clippy lint was suppressed. The following feature Clippy run passed.
The final sealed receipt retains the complete final Clippy output.

Independent source review then identified that the final cancellation check
cleared `construction_bytes` immediately before Rust implicitly dropped a
completed unpublished entry. The final code now explicitly drops that entry
before clearing its construction reservation. This is a strict accounting-order
correction; cancellation and allocation-injection tests are rerun in the final
receipt. Reviewer findings/evidence live in its separately owned
`verification/span-function-cache-review/` directory.

These are transcribed diagnostic excerpts from the development tool trace, not
claimed as complete raw logs from those earlier invocations. The final receipt
records exact commands/output hashes against a stable source manifest.
