# Preaccess configuration assessment

This assessment uses only the frozen protocol, original baseline source and root's
described configuration issue. The implementation directory has not been opened.
It is an assessment of a proposed bounded test configuration, not a source review
or test pass. Root reports that original `cfg(test)` adds 48 bytes to AccountedWasi,
affecting selected IDs 122 and 160 (1,496 versus 1,448) and caller ID 146
(12,360 versus 12,312). Those three measurements were **not** freshly produced by
this independent lane. Its old-source driver compiles without `cfg(test)` and
does not measure the 165 new complete types.

No concrete contract flaw is apparent in qualifying production-layout success
through a finite non-test dispatcher and original typed fault controls through
the original test configuration. The frozen contract permits separately named
explicit test-only complete records, and the production selected literals remain
binding. Acceptance still requires all of the following observations:

1. Fresh actual size **and alignment** measurements for all 165 types in Debug
   and optimized modes of both configurations; exactly the three reported IDs
   must differ, with no additional unreviewed delta.
2. Any test-only full table must be independently root-selected immutable literal
   data, with every field explicit. Fresh measurement must never create expected
   values for the comparison. The selected production producer and its static
   table remain exact and must never return the test record.
3. The original production selection must explicitly refuse with local error 6
   under `cfg(test)`. Fault tests may use the separately selected test record but
   cannot call that evidence production-layout success.
4. The custom dispatcher must have an exact closed signature, fixed method roster
   and recorded host runner invocation, be absent from normal product builds,
   and expose no owner/guard/proof/reference/callback/reentry seam. Every source
   variant, test-only insertion, env, argv, compiler and executable is retained.
   The exact dispatcher proposal remains pending root selection/source review.
5. Independently close the actual caller/place/lifetime/work/I/O/cleanup join for
   each configuration under unchanged original bounds and deadlines. Passing a
   comparator, a data model or one configuration cannot substitute this proof.

Root subsequently selected the split, exact dispatcher and immutable test table
through the hash-bound inputs in `configuration-selection-custody.json`. The
independent comparison of those two fixed JSON tables observes exactly IDs
122/146/160 with size +48 and unchanged alignment; this is data comparison only.
The actual-source and measurement conditions remain pending. No new selection
follows from this assessment itself. No broad tests, native runtime, capture or
process inventory was run.
