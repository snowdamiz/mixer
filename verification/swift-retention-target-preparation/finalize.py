#!/usr/bin/env python3
"""Seal already completed preparation evidence; no compilation or guest execution."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
from packetlib import (HERE as H, ROOT, CANDIDATE_SEAL, CANDIDATE_CLOSURE,
                       LIVE_BASELINE_CLOSURE, HARNESS_HASH, closure, read, sha,
                       verify_candidate)

assert not (H/'owned-scratch').exists() and not (H/'bin/exact-tests').exists()
assert not (H/'root-selection.json').exists() and not (H/'target-attempt-started.json').exists()
assert not (H/'commands/target-once').exists()
assert not (H/'prepared-seal.json').exists()
verify_candidate()
def save(name,value):
    (H/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
binding=read(H/'binding.json')
binary=read(H/'binary.json')['retained']
cleanup=read(H/'cleanup.json')
proposal=read(H/'prepared-selection.json')
command=read(H/'proposed-command.json')
build=read(H/'commands/build-001/receipt.json')
events=read(H/'control-001-events.json')
by_name={event['event']:event['payload'] for event in events}
budgets={key:by_name[key] for key in ('validation_budget','run_budget','wasi_budget')}
assert budgets['validation_budget']['deadline_ms']==120000
run=budgets['run_budget']
for key,value in {'active_pins':64,'cache_entries':64,'cache_bytes':16777216,
                  'cache_entry_bytes':8388608,'cache_work':64000000,
                  'combined_bytes':268435456,'deadline_ms':30000}.items():
    assert run[key]==value
assert budgets['wasi_budget']['deadline_ms']==30000
save('proposal-scope.json',{'schema':1,'candidateManifestSHA256':CANDIDATE_CLOSURE,
    'liveBaselineClosureSHA256':LIVE_BASELINE_CLOSURE,'candidateSealSHA256':CANDIDATE_SEAL,
    'candidateLiveIntegrated':False,'independentReviewStatus':'separate finalized acceptance required before root selection',
    'sameBudget':budgets,'liveTicketsCap':86,'outerDeadlineSeconds':170,'exactGroupCleanupSeconds':10,
    'phaseSequence':['validation','adoption','construction','Initialize35','Corpus62','Corpus62','consuming cleanup'],
    'nativeOracleFields':11,'harnessSHA256':HARNESS_HASH,'observerRequired':False,
    'knownFiniteTradeoffs':binding['finiteTradeoffs'],
    'inferenceBoundary':'Finite traces do not establish target improvement. The isolated retention policy can regress cyclic traces and increases resident-hit work. No budget is widened or accounting credit waived.',
    'fullTargetAttempts':0,'targetSelected':False,'nativeAccepted':False,'gaAccepted':False})
template=proposal | {'exactCommandSelected':False,
    'preparedSealSHA256':'ROOT_FILL_FINAL_PREPARED_SEAL_SHA256_AFTER_INDEPENDENT_REVIEW',
    'rootSelectionAuthority':'fresh-root-selection-after-accepted-independent-review',
    'selectedUTC':'ROOT_FILL_FRESH_TIME_AFTER_BOTH_SEALS',
    'sourceManifestSHA256':sha(H/'copied-build-manifest.json'),
    'compilerTools':binding['compilerTools'],
    'reviewSealPath':str(ROOT/'verification/swift-cache-retention-review/seal.json'),
    'reviewSealSHA256':'ROOT_FILL_FINAL_ACCEPTED_REVIEW_SEAL_SHA256',
    'reviewSummaryPath':str(ROOT/'verification/swift-cache-retention-review/result-summary.json'),
    'reviewSummarySHA256':'ROOT_FILL_FINAL_ACCEPTED_REVIEW_SUMMARY_SHA256',
    'proposalScopeSHA256':sha(H/'proposal-scope.json'),
    'templateIsNotSelection':True}
save('root-selection-template.json',template)
host_tools={}
for name,path in [('lsof','/usr/sbin/lsof'),('ps','/bin/ps')]:
    p=Path(path);host_tools[name]={'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),
        'platformVersion':binding['compilerTools']['system']}
probe=subprocess.run(['/usr/sbin/lsof','-v'],capture_output=True,timeout=5)
(H/'lsof-version.stdout').write_bytes(probe.stdout)
(H/'lsof-version.stderr').write_bytes(probe.stderr)
host_tools['lsof']['versionProbe']={'argv':['/usr/sbin/lsof','-v'],'exitCode':probe.returncode,
    'stdoutSHA256':sha(H/'lsof-version.stdout'),'stderrSHA256':sha(H/'lsof-version.stderr')}
save('host-tools.json',host_tools)
source_hash=sha(H/'copied-build-manifest.json')
source_archive_bytes=(H/'prepared-source.tar.gz').stat().st_size
compressed_bytes=(H/'bin/exact-tests.gz').stat().st_size
logical_removed=cleanup['logicalBytesRemoved']+binary['bytes']
receipt={'schema':1,'status':'prepared-awaiting-accepted-independent-review-and-fresh-root-selection',
    'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'rootSuppliedRevision':'b375e55ded9e3e10c327891ab681beff2a471e26',
    'candidateSealSHA256':CANDIDATE_SEAL,'candidateManifestSHA256':CANDIDATE_CLOSURE,
    'liveBaselineClosureSHA256':LIVE_BASELINE_CLOSURE,'candidateLiveIntegrated':False,
    'sourceFiles':132,'copiedBuildManifestSHA256':source_hash,'harnessSHA256':HARNESS_HASH,
    'driverSHA256':sha(H/'diagnostic.py'),'binarySHA256':binary['sha256'],'binaryBytes':binary['bytes'],
    'retainedSourceArchiveBytes':source_archive_bytes,'retainedBinaryGzipBytes':compressed_bytes,
    'noRunReleaseBuildPassed':True,'buildSeconds':build['durationSeconds'],
    'syntheticHarnessControlsPassed':2,'syntheticGuestInstructionsPerControl':5,
    'inheritedHostProcessControlsPassed':10,'mockedReviewGuardTestsPassed':8,
    'rootSelectionCreated':False,'independentReviewRequiredBeforeSelection':True,
    'fullTargetAttempts':0,'targetModuleUsedAsDataOnly':True,'compilerTargetRemoved':True,
    'cleanup':{'scratchAbsent':True,'uncompressedBinaryAbsent':True,'compilerTargetAbsent':True,
        'sourceAndBinaryArchivesRetained':True,'holderChecksEmpty':True,
        'ownedGroupSignalsSent':False,'logicalBytesRemoved':logical_removed},
    'knownTradeoffs':binding['finiteTradeoffs'],
    'originalSupervisorParserAndConsumingHarnessCleanupUnchanged':True,
    'inheritedPrepareCLIEnabled':False,'originalPacketsExecutedRestoredOrMutated':False,
    'liveVMReadOrWritten':False,'rootIndicesModified':False,'gitUsed':False,
    'networkUsed':False,'nativeUIOrDeviceRuns':0,'hostedOrFrozenLanesAccessed':False,
    'nativeAccepted':False,'publishedPackageFieldLogQualified':False,'gaAccepted':False,
    'entrypoints':{'readOnlyVerifier':'verify.py','ownedRestorationOnly':'restore.py',
        'proposedCommand':'proposed-command.json','rootSelectionTemplate':'root-selection-template.json',
        'sourceArchive':'prepared-source.tar.gz','compressedExactExecutable':'bin/exact-tests.gz'},
    'finalization':{'argv':[sys.executable,'-B',str(H/'finalize.py')],
        'scriptSHA256':sha(__file__),'pythonSHA256':sha(sys.executable),'pythonVersion':sys.version}}
save('receipt.json',receipt)
doc=f'''# Isolated retention-candidate full Swift diagnostic preparation

Prepared for root review and a later exact selection. **No full-target attempt
has been selected or executed.** The candidate is not integrated into the live VM.
The packet is `verification/swift-retention-target-preparation/`.

Root supplied revision context `b375e55ded9e3e10c327891ab681beff2a471e26`.
The live baseline closure is `{LIVE_BASELINE_CLOSURE}`;
the separate 132-file candidate closure is `{CANDIDATE_CLOSURE}`, from candidate
seal `{CANDIDATE_SEAL}`. The candidate seal and every member/external member were
checked as data. No Git query or live VM source read occurred. Root indexes are
archived context observations, not mutable seal inputs.

The only preparation source change is an absolute include of the original harness
at the end of the candidate's lifecycle test file. The copied build manifest is
`{source_hash}`. The harness remains byte-identical to
`verification/swift-exact-reactor-after-plan-reuse/harness.rs`, SHA-256
`{HARNESS_HASH}`. The newer attribution harness and observer are not used.
The original workload, native eleven-field oracle, parser, event emission,
phase sequence and Rust consuming cleanup remain exact. Original host tools,
process supervisor, parser, build, cleanup and ten host tests are literal copies;
the [driver diff](../verification/swift-retention-target-preparation/driver-changes.diff)
records isolated paths/source bindings, labels and the fresh review/selection guards.
The inherited prepare CLI and old live-source copying procedure were removed.

## Executable preparation evidence

The fresh offline Release no-run build passes in {build['durationSeconds']:.3f}
seconds with two Cargo jobs. Listing selects exactly the original tiny control
and target test names. Cargo/Rust 1.99.0, Python 3.14.8, macOS 27.0.1 arm64,
tool identities, sysroot hashes, source manifests, exact argv, environment,
raw streams, process groups and deadlines are retained in the binding and receipts.

Both unchanged tiny synthetic harness controls pass. Each executes synthetic
Initialize once and Corpus twice, five guest instructions, and consuming cleanup
to zero current reservations, live tickets and live counts. They prove wiring
and cleanup only. The ten original mocked process observation tests pass;
eight additional host-only tests check accepted-review prerequisites, drift,
candidate/baseline substitution, historical path rejection and safe archive names.
Those eighteen host tests execute no guest instructions.

The initial assembly attempt rejected the source archive's timestamp-only PAX
metadata before source restoration or compilation. Its streams and exact scripts
are retained. The extractor now permits only bounded finite `mtime` metadata;
path/link metadata, duplicate or unknown names, links and non-regular files fail
closed. Extraction is limited to 132 members, 24 MiB total, 16 MiB per member and
a 2 MiB compressed archive, with every content hash checked before writes. The
corrected assembly, first build and every executable control pass.

## Exact proposal and selection boundary

The [proposed command](../verification/swift-retention-target-preparation/proposed-command.json)
uses the retained {binary['bytes']:,}-byte executable, SHA-256 `{binary['sha256']}`.
The outer command, still unselected, is:

```sh
python3 -B verification/swift-retention-target-preparation/diagnostic.py target
```

Its child argv selects only the original `exact_reactor_target_once` test with
`--exact --nocapture --test-threads=1`. Validation stays 120 seconds; runtime and
WASI stay cumulative 30 seconds. The outer limit stays 170 seconds plus the
original bounded 5+5-second exact-process-group cleanup. Residents/pins stay 64,
tickets 86, cache/entry limits 16/8 MiB, cache work 64 million and combined memory
256 MiB. All other original ceilings are retained. Initialize 35 and Corpus 62
twice share the same owner and cumulative accounting lifetime.

The 53,777,114-byte target remains immutable data, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
It was hashed, never validated, compiled, instantiated or executed in this lane.
The native oracle output was read as historical data; no native oracle ran.

The [scope binding](../verification/swift-retention-target-preparation/proposal-scope.json)
preserves candidate tradeoffs: the hot-plus-scan trace used 6.3192% fewer cache-work
credits, cyclic 65 used 2.1100% more, and the cyclic 64 resident-hit work ratio was
22.7773. These finite traces do not establish actual-target improvement. No
budget or credit is relaxed to accommodate the policy.

The root-selection template deliberately refuses dispatch. Root must first
independently accept this sealed preparation and the finalized accepted review at
`verification/swift-cache-retention-review/`. The target guard hashes that review's
seal, summary and all sealed members, requires its finite acceptance with no
blocking findings, checks both distinct source closures and the original candidate
seal, and rejects target/integration/GA selection in that review. A new root
selection must bind the exact preparation seal, copied source manifest, executable,
harness, driver, tools, input binding, argv and budgets. Its timezone-aware timestamp
must follow both final seals. Historical root selections authorize nothing here.
The exclusive `target-attempt-started.json` marker permits one actual attempt;
neither it nor a root-selection file exists.

## Retention, cleanup and pending work

The source is retained as a verified {source_archive_bytes:,}-byte gzip archive;
the exact executable is retained as a verified {compressed_bytes:,}-byte gzip.
All compiler products, the owned scratch tree and the uncompressed executable
were removed after exact scoped holder checks and device/inode checks. Cleanup
removed {logical_removed:,} logical bytes. Every preparation-owned process group
was observed absent, and no signals were needed. Other projects' processes and
native instances were not touched.

`restore.py` first runs the read-only verifier, then restores only these exact
products under this packet's `owned-scratch/vm` and `bin/exact-tests`. It refuses
existing products, selection or attempt markers, and never builds or runs code.
Root should archive its later attempt and cleanup evidence in a separate result
namespace; do not rerun preparation build/control/proposal/cleanup actions after
selection or overwrite these preparation receipts.

```sh
python3 -B verification/swift-retention-target-preparation/verify.py
python3 -B verification/swift-retention-target-preparation/restore.py
```

The first command only reads and hashes. The second is an optional bounded owned
restoration for root review; it was prepared but not executed by this lane.
Root alone selects any later target command after accepted independent review.
No source/product integration, Git, network, hosted/frozen lane, native/UI/device,
signing, publication or customer action occurred. Actual target benefit, full
regression, published-package FieldLog qualification, physical phones and all
accountable GA gates remain pending. This is preparation within W08 and preserves
the binding W01–W18/G01–G38 product scope.
'''
docpath=ROOT/'docs/swift-retention-target-preparation.md'
docpath.write_text(doc)
files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file()}
assert 'prepared-seal.json' not in files and 'root-selection.json' not in files
externals={str(Path(info['path']).relative_to(ROOT)):info['sha256'] for info in binding['inputs']}
externals[str(docpath.relative_to(ROOT))]=sha(docpath)
save('prepared-seal.json',{'schema':1,'sealedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope':'preparation only; zero target attempts; no candidate live integration',
    'candidateManifestSHA256':CANDIDATE_CLOSURE,'liveBaselineClosureSHA256':LIVE_BASELINE_CLOSURE,
    'candidateSealSHA256':CANDIDATE_SEAL,'files':files,'externalFiles':externals})
print(json.dumps({'preparedSealSHA256':sha(H/'prepared-seal.json'),'members':len(files),
                  'externalMembers':len(externals),'fullTargetAttempts':0,
                  'sourceManifestSHA256':source_hash,'binarySHA256':binary['sha256']}))
