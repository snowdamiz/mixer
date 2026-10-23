# Corrected foundation qualification

The root-level `receipt.json`, `inputs/` and `logs/` preserve the first attempt.
The no-feature and legacy span suites passed. The Swift suite passed 105 tests
and failed one cache layout assertion that still summed only the historical
seven foundation classes. It observed 17,368 rather than 16,504 bytes.

Candidate 2 adds the new named final-boundary allowance to that assertion and
prints it separately. The metadata constant is visible only to the parent
private module so sibling cache tests can name it. No owner layout, runtime
algorithm, cache allowance or reservation rule changed in that correction.
Candidate 2 runs from a fresh source archive; the original failed receipt is
not rewritten as a pass.

`qualify.py` freezes complete VM inputs and runs six feature combinations in
Debug and Release. The all-features runs include integration and documentation
tests. Focused tests record three admission boundaries and seven cleanup cases
with actual WASI observations, and retain the original executor prerequisite
tests. Separate derived production metadata uses the real inventory definitions;
it adds only a metadata print function and example, never a runnable executor.
Its overlay hashes and exact source are recorded. Negative external consumers
verify that the Swift owner and Swift-only legacy module remain private.

Independent corrected-source review lives under
`../swift-executor-final-accounting-review/root-correction/`. Root acceptance is
separate. No target initialization, invocation, device or GA evidence is implied.
