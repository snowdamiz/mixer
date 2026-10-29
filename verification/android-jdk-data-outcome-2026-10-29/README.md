# Android JDK data observation outcome

Revision `47b62878` delivers the 74-path diagnostic slice. Standard CI 40863262879 passes all six jobs. One separately selected data-only diagnostic, 40863640582, succeeds. Exact outer audit confirms 13 files and 74 complete source-bound observations, with 72 whole-file hashes matching the immutable official release.

The completed comparison preserves all 13,653 ct.sym file names and payloads; 204 empty directory names change from double to single trailing slash. All 61 jrt-fs.jar entry names and payloads match. Compression and metadata differ. The 104 guarded controls and 329 independent actual data checks support preparing a separate exact package-observed profile. Original runtime pins remain unchanged and no Java run is admitted here.

The job log and observed environment disagree on image version. Older focused-run bytes, packaging cause and provider provenance remain unknown. Acquisition, audit and comparison failures and consumed allowances remain recorded. No focused 13/152, canonical pair, native, immutable FieldLog, OTA or GA acceptance follows.

See [observation](observation.json), [ordinary CI](ordinary-ci.json), [comparison](../android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/result-summary.json) and [independent review](../android-jdk-comparison-challenge/ACTUAL-RESULT-REVIEW.md).
