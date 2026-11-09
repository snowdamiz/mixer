ACCEPT_EXACT_PLATFORM_HOST_CI_SOURCE

Fresh independent Sol 6.1 xhigh review accepts only the exact five-path R3 platform-host candidate for root adoption and a new ordinary official-JDK17 android-owner-host job. No blocking source finding remains. This is source/fake-boundary acceptance, not canonical installation, compiler evidence, CI success, native acceptance or GA qualification.

Exact source and package identity

Candidate directory: ../profile10-platform-host-unknown-latch-fix-r3/.
Full candidate.patch: 85,338 bytes; SHA256 bddf82c212ae4934fdc7d4da9785e3b53b553fb33880ff240be25408f56877e0.
R2 increment: 29,495 bytes; SHA256 e84d538bfd41beaa36aefced3f712246796b9ce1a5cec5f7b96bbb1d60a28858.
Candidate seal.json: 698,424 bytes; SHA256 120a7fe9ce98bd998eddb42a8bc125b0db6b2d0df254cbe766797bede6385e81.
application-map.json: 1,794 bytes; SHA256 54babd66040f258bf614b3ad1802b0cb284b2dab7286d7020b46d17291c8b665. The exact map is copied into this review directory. candidate-seal-identity.json binds these identities and the tested source tree.
The inherited five-path baseline is 924b155f9d319bb9bbee2b4e082960706edbfb25; no live Git/HEAD assertion is made.

Exact five final paths, with byte counts and SHA256:

- native/android/tests/run-environment-platform-host.py: 10,418; 33b3964a3d3f4faed181dfacf32d1df415061618483d4951847c328c72d9c405.
- native/android/tests/run-environment-observer-host.py: 5,592; 595f69458f8272ec61aa1ddb80359cce08b9c5fa61346e5dc4db496b7633a57f.
- native/android/tests/environment_host_commands.py: 12,414; cde0b8e751ae390a1f3fb31d65bdc3744654db369cc83f1f2c27ed347e14b39f.
- native/android/tests/test_environment_host_commands.py: 41,452; 0d78d8372f8565613c2b93e3fea5b47e4ec43293bfdec6b9757ac79b4839b4c6.
- native/android/tests/NativeEnvironmentV2ObserverHostLeaves/dev/mixer/android/AppearanceResolverV2.java: 553; 86b027d6b3996c5acd5756f90135b1499def45599ba6f2c888ba5da6f8f92182.

Independent audit.mjs strictly replays the full five-path patch and two-path R2 increment, checking exact paths, duplicate/missing paths, old/new headers, offsets, context/deletions, hunk counts and final bytes. All three canonical existing-file preconditions and both absent-new-file preconditions pass before and after testing. Only the wrapper and its source test differ from R2; both harnesses and the Java leaf remain exact R2 bytes. The report, map and seal are identified; the 233 execution-overlay files are checked against the corresponding candidate seal entries. This does not claim a recursive audit of every historical file named in the candidate's large seal.

All 228 unchanged host-overlay dependencies match current canonical bytes. The separate 76 relevant profile/SDK/adapter pins also match. The tested 233-file overlay digest is d581329ca3ef1e72912b4e445c2a3569f3d3594a0594ef595c46a35275416fde (SHA256 of the ordered 41,820-byte JSON identity list in audit-before.json). All 242 executable/source/package inputs remain identical after both modes. audit-before.json and audit-postflight.json are identical in result. Root mutable tracking is excluded. No unrelated CLI106/CLI113 closure is used as a host-admission or adoption authority.

Source conclusions and executable evidence

The reviewed wrapper is tree/native/android/tests/environment_host_commands.py. latch_unknown at line 97 closes admission and retains the first hold and exception object before callbacks. Unresolved in-memory command records become UNKNOWN and remain nonterminal. run at line 147 latches uncertainty from actual hold/custody state; it does not infer custody from error strings. finish at line 177 caches its result at line 206 before HOLD persistence and never calls the installed adapter again after a cached outcome. finalize at line 213 fences re-entry, performs source postflight at line 223 before cleanup, and caches its final receipt at line 241 before receipt persistence. Repeated completed finalizers perform no source, process or persistence callbacks. Recursive in-progress finalization is refused. check_open at line 129 prevents late admission before executable or selector access. useful_work at line 134 enforces the 2.0-second floor both before and after admission persistence, with 60 cleanup seconds additional.

Two complete payloads ran against identical final candidate bytes:

- normal: the candidate's actual main entrypoint PASS 17/17 groups; independent review controls PASS 4/4 groups.
- optimized (-O): the same actual main entrypoint PASS 17/17 groups; identical independent controls PASS 4/4 groups.

The actual main was executed with runpy; only its exit call was captured so the independent groups could run in the same bounded payload. All test assertions remain active in -O through unittest. review_controls.py is the review reproducer; the candidate source test was not edited.

The original six-group byte prefix is unchanged: SHA256 9741401dbf2779a7ae58903d6e1c9ea42bc40102d2ace086f8f501f260928a32. The original eleven corrected assertion bodies remain byte-identical: SHA256 be90e78e6fa73494dd0f7f060b9fbbecb6927c73815cb3d87d433c3eb5f2ab82. The exact prior reviewer one-shot correction and both targeted bodies were compared independently. No assertion was removed or weakened. The normal main contains and executes all seventeen groups.

Both actual harness entrypoints and the installed adapter execute through fake nested tools/processes. Controls retain failure/UNKNOWN receipts, scratch and first causes while exercising persistent cleanup interruption; cleanup OSError/KeyboardInterrupt/SystemExit; explicit incomplete cleanup with no prior hold; existing UNKNOWN combined with source and receipt faults; HOLD-write failure; and callbacks re-entering finish/finalize/prepare/add_plan/run from source reads, adapter cleanup, HOLD persistence and receipt persistence. The additional independent groups start unresolved synthetic command records before injecting each cleanup exception, check first-cause/hold object identity and final UNKNOWN/nonterminal memory state, and combine existing holds with OSError/KeyboardInterrupt/SystemExit source and receipt failures. All later launches and synthetic process/group operations remain zero. Cached terminal cleanup also performs no later operations. No RUNNING or UNKNOWN outcome is accepted as PASS.

Positive one-shot interruption still requires direct reap, independent stdout/stderr EOFs, positive synthetic group absence and both closed descriptors. KeyboardInterrupt and SystemExit propagate, and multiple cleanup pump calls are required. Below-floor cases at 0.25 and 1.999 active seconds refuse; exactly 2.0 seconds admits an immediately completing fake; a 0.001-second persistence delay consumes that floor and refuses launch. These are admission hypotheses, not measured JVM startup capacity or completion guarantees.

The retained R2 red baseline was inspected, not rerun: both harness counterexamples retain durable UNKNOWN/HOLD with null internal hold and one additional fake SIGKILL group event on repeated finish. Earlier failed receipts and review findings remain historical evidence. No actual JVM or native run was repeated.

Persistence evidence has explicit limits. Failed final-receipt writes remain failed, even though the cached in-memory outcome stays UNKNOWN. The deliberately failed HOLD-write control has no HOLD.json; its receipt records the persistence error, and its in-memory owner remains UNKNOWN. Separately, persistent interruption before the installed adapter's final persistence can leave commands.json at its original RUNNING launch snapshot. This was observed in both modes and is preserved in persistence-observation.json. Final in-memory command records remain UNKNOWN/nonterminal and durable HOLD/receipt remain UNKNOWN; the stale command snapshot is not a terminal receipt. No claim is made that every on-disk command record was rewritten to UNKNOWN. This observation did not reopen admission, repeat cleanup or produce a pass.

Actual profile, compiler and isolation contracts

Both Observer and platform environment rosters contain the actual AndroidUIProfile.java exactly once, with no duplicate source path or FQCN and no substitute profile. Independent checks also cover A/B/cross closures. Platform source_closure is at line 21; Observer SOURCES at line 27. The actual profile enum bytes remain canonical. The sole Java leaf change remains reducedMotion to the actual reduceMotion accessor.

Strict compilation remains --release 17, -Xlint:all, -Werror, -proc:none, -J-XX:ActiveProcessorCount=2, bounded memory, and empty host classpath/sourcepath (platform line 74; Observer line 62). Runtime processors remain two. The platform forbidden-symbol list at line 97 is byte-equal to the canonical list after indentation; its existing Api-family exception at line 100 is unchanged. No new broad compatibility exception was introduced.

The installed adapter remains SHA256 26ea5a8aa5b51c897ad7bd45ecde2162ee2ba45d4dedc5d713fb76783ad72b03. Installed and runner custody copies remain 8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df. Actual A/B dispatcher bytes remain 0766988f630883da5e60118ce18a05afcef6f1a7eadae92aa340d9660bf71b3f. The actual installed entrypoint is loaded in process, with its tool-running main intercepted. No full A/B matrix or Java oracle was replayed. Both Java oracles remain pinned canonical inputs.

Four historical evidence files were hash-checked. Retained results remain 190 Observer cases and 134 platform cases/699 assertions under historical JDK25 --release 17. Direct text/manifest audit confirms 179 manifest entries, 21 emitted environment-family sections, 15 non-Api checks, six pre-existing Api exclusions and no forbidden-symbol violations in the retained non-Api dumps. Deleted class bytes were not rehashed or recreated. The separate six Java/D8 consumers and their 219-class counts are not requalified by this review. historical-audit.json records these boundaries.

Bounds, custody and cleanup

The finite campaign used two of four allowed payload slots, 180 active seconds plus 60 cleanup seconds, each actual payload capped at 40 seconds. Command/aggregate output caps remain 8 MiB/64 MiB. Actual combined payload output is 10,990 bytes. Each complete prelaunch.json was fsynced before the first terminal transport, including exact argv, source/tool hashes, output/scratch device+inode identities and a fresh deadline. The supervisor rechecked executable availability before launching its payload. Both commands started before the recorded active deadline. No expired deadline or extra payload was used.

The payload tool is Homebrew Python 3.14.8 on macOS arm64; executable SHA256 e401ac7a95cda75dee34a0cfe1e4faf0a6df1a501cf67887f177fb78cd4eb60a. Fake java/javac/javap symlinks resolve to that pinned executable; every nested launch and group operation is intercepted. The exact pinned custodian alone launched each real payload child. Both receipts are TERMINAL with direct reap, separate EOFs, positive owned-group absence, closed stream completion, no signals, no cleanup errors and no hold. Only then was each exact owned outer scratch directory removed. Unknown/failed inner test scratch is synthetic and retained; teardown closes only synthetic descriptors. No process/group was probed again after terminal receipts.

The primary execution transport starts the supervisor outside its child custodian. Payload receipts do not prove primary transport reap/EOF/group absence, provider disposal or arbitrary escaped-descendant absence. Those limits are explicit. No local preparation failure, payload failure, blind retry or fixture correction occurred in this review.

Root adoption recipe and next gate

1. Recheck the pinned candidate patch/map/seal and all current canonical before/absent preconditions immediately before adoption. Rerun this review's pure filesystem verify() if helpful. A changed path/hash or package requires a new scope decision; this acceptance is exact-byte only.
2. Install exactly the five application-map paths from the sealed candidate, preserving every other root/other-lane change. Neither execution tree is a bulk adoption payload. Do not apply the R2 increment to canonical: its preconditions describe R2, which is not installed. Verify all five after hashes and both unchanged adapter/custodian pins after installation.
3. Root updates canonical tracking and delivers a coherent validated slice under its existing authorization. Root alone owns commit/push and inspection of the resulting ordinary CI; this reviewer performed none of those actions.
4. Run the existing Android platform observations and observer host regressions workflow step in android-owner-host with the official JDK17 environment. The command is python3 -B native/android/tests/run-environment-platform-host.py --jdk "$JAVA_HOME_17_X64" --evidence "$RUNNER_TEMP/android-owner-environment", after requiring JAVA_HOME_17_X64. Actual JDK17 CI remains pending. This review accepts the source prerequisite for that new job, not the old failed CI42545709402 or any whole-CI result.

Only profile10-platform-host-r3-review/ was written. No canonical/predecessor/candidate/other-lane write or self-source fix/adoption occurred. No compiler/JVM/native/AX/ADB/device/UI/ports/process enumeration/network/Git/provider/CI/delegation/commit/push/customer/publication action occurred. Physical phones remain disconnected. No historical held group or scratch namespace was inspected, enumerated, probed, signalled, retried or cleaned. CLI/TestFlight, Swift frozen callers, specific historical holds, native/runtime, immutable separate-repository FieldLog packages, final physical phones and GA remain outside this acceptance.
