# Declare the complete Java host inputs

NativeEnvironmentPlatformV2.java is already compiled by both host runners but was omitted from their declared A/B production rosters. Direct roster consumers therefore fail with a missing-type error. Add the existing file to both declarations and remove the separate injections from the runners. Exact old/new explicit javac input sets are equal; SDK/product bytes and owning source116 are unchanged.

Both declared-only closures compile strictly. A host passes. The root B host check reached its 120-second timeout, below the established runner's 300-second allowance; no output or product defect was established. Its owned process group was confirmed absent after termination, and scratch removed. The complete existing Android owner CI job passes on b898d3c3 with the same compiler source set. No repeated B execution is selected for this metadata-only correction.

Patch remains private until active source lanes finish their input comparisons. No native, package or GA qualification. The initial pure preparation script also failed on an incorrect A-roster insertion anchor; corrected before any compile or canonical write.
