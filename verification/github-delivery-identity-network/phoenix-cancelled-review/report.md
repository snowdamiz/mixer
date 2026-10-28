Phoenix run 40723227254 / job 122939477520 remains cancelled at commit
756695fb9b0f6ec85d978202e2b3c586aa3db16f (Git tree e7067a813247496091dc56f4903de77f7242b645).
This packet reviews retained evidence only; it provides no new runtime acceptance.

- Retained artifact 12831598909: 1,470,518 bytes; SHA-256
  23c747645e5b6523411710454d3edfcf149a0987440d5522ca692c1690c50b0a.
  All 273 ZIP entries (3,392,338 expanded bytes) were validated for relative paths,
  no traversal/backslash/duplicate/symlink/encryption, expansion cap and CRC, then
  safely extracted. The nested source archive was independently validated under
  the 64 MiB cap; its 181 files (4,578,681 bytes) all match exact committed blobs.
- Current protocol: 45 passed, no failed/skipped/excluded tests; current storage:
  24 passed; current migration: 1 test, 0 failures/skipped/excluded. Source maps
  of 14, 13 and 23 files respectively match exact committed blobs. Migration
  receipt output hashes (31 files) and command log hashes match retained bytes.
- Last foundation trace: tests.log line 1323 enters KeyOwnerTest K08b,
  “eight configured profiles cannot open a fifth owned flight.” The last completed
  trace is K08 (324.1 ms), line 1322. There is no K08b completion, suite summary,
  source-unchanged result, final foundation receipt, or postgres-stop log. This
  does not prove that K08b failed, hung, or caused cancellation.
- Checkout spans 16:09:54.019536Z to the next action at 16:21:17.898163Z:
  683.878627 seconds (upper bound). Fetch occupied 616.349470 seconds;
  writing 338,637 files occupied 66.461304 seconds. The committed workflow has
  a 15-minute job limit. The foundation step began at 16:22:23.634724Z and was
  cancelled at 16:25:05.864019Z, after 162.229295 seconds. No collector 300-second
  timeout marker exists. Timing supports possible job-budget exhaustion; the
  cause is not explicit and the recorded conclusion remains cancelled.
- Protocol scratch cleanup, storage PostgreSQL/scratch cleanup, and migration
  PostgreSQL/scratch/compile-product cleanup are recorded true in their own
  current receipts. Foundation cleanup is unproven. Runner log lines 564–569
  report orphan termination for Python, PostgreSQL, BEAM, erl_child_setup and
  two inet_gethost processes; those are termination attempts without retained
  post-termination absence evidence. Per-case lifecycle observations apply only
  to their named resources and do not prove whole-collector cleanup.
- Nine historical receipts (2 protocol, 7 storage from October 25) arrived via
  broad recursive upload of tracked attempt directories. They are explicitly
  excluded from the current runtime verdict.

Reproduce only the offline review with `python3 /Users/andreyyurlov/Documents/dev/mixer/verification/github-delivery-identity-network/phoenix-cancelled-review/review.py`.
The recorded command, Python/Git versions, output hashes, exact source bindings,
timing markers, log bindings and limitations are in review.command.json,
source-bindings.json, timing.json, log-bindings.json and review.json.
No rerun/dispatch, product runtime, Docker/PostgreSQL/native/UI/capture/process
inventory or writes outside this packet occurred. No Git/index/metadata/memory
changes were made. No GA or customer acceptance is established.

Acquisition incident: the first connector result was accidentally emitted to the
tool transcript, exposing its temporary signed file-reference URL. The URL was
not persisted in this packet; subsequent acquisition output was sanitized.
