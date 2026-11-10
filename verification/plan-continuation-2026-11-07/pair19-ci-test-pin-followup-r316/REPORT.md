# Pair19 CI test-pin correction

The first hosted Pair19 run at 1a56d6d0 failed two current-profile tests that still expected Pair18: generated-java bootstrap and the CLI source-compatibility session test. The latter also pinned Pair18's old SDK/adapter digests. Both tests now pin the exact Pair19 identity and its accepted digests; all 24/27 roster and DocumentSession byte assertions remain. Historical-version negative cases remain unchanged.

R308 independently reproduced the bootstrap mismatch and prepared the four-file caller/seal correction. It passed 148 controls across normal/optimized Python plus both installed guards. Root applied those exact files and updated the separate CLI compatibility test. All 22 compatibility tests passed in normal Python and actual -O, with both exact process groups observed absent. The initial local digest-pin failure is retained under baseline-digest-pin/.

The owning source116 remains ee43817e481398db35a4c60b8416c647745b9be0e46fa2c8f4390900c4999e99. Product/compiler/runtime bytes, SDK24, adapter27 and Java21 are unchanged. Existing R300 actual six, R304 actual V4 build, R292 full SDK and R276 owner regressions therefore remain the exact product evidence. This follow-up changes tests/caller authority and records a newly scoped cache hold; it grants no GA qualification.

The separate cache job failed with EPERM/UNKNOWN for run42883750881/job130066539843 PID/PGID1143. R310 records only copied top-level summaries; the group and scratch remain held. No hosted retry, probe, signal or cleanup was performed. Root continues independent app/native work.
