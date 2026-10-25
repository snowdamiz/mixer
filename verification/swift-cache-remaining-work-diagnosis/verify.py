#!/usr/bin/env python3
"""Check this diagnosis packet; never compile or execute guests."""
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
seal = load(HERE/'seal.json')
for name, expected in seal['files'].items():
    assert sha(HERE/name) == expected, name
for name, expected in seal['externalFiles'].items():
    assert sha(ROOT/name) == expected, name
for name, expected in load(HERE/'input-bindings.json').items():
    assert sha(ROOT/name) == expected, name
baseline = load(HERE/'live-source-before.json')
assert baseline == load(HERE/'live-source-after.json') and len(baseline) == 132
assert sha(HERE/'live-source-before.json') == 'b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
for name, expected in baseline.items():
    assert sha(ROOT/'vm'/name) == expected, name
rows = [json.loads(line.split('REMAINING ',1)[1]) for line in (HERE/'fixture.stdout').read_text().splitlines() if 'REMAINING ' in line]
assert rows == load(HERE/'fixture-observations.json')['observations']
assert [row.get('work') for row in rows[:-1]] == [205,3,286,3,15335,66,129,30888]
for row in rows[:-1]:
    assert sum(row['stages']) == row['work']
    assert row['stages'][2] == row['stages'][4] == 0
assert rows[-1] == {'cleanup':'four_original_owners_drained'}
assert (rows[4]['decodes'],rows[4]['hits'],rows[4]['evictions']) == (64,64,0)
assert (rows[7]['decodes'],rows[7]['hits'],rows[7]['evictions']) == (130,0,66)
command = load(HERE/'fixture-command.json')
assert command['exitCode'] == 0 and not command['timedOut']
assert command['signalsSent'] == []
assert sha(HERE/'fixture.stdout') == command['stdoutSHA256']
assert sha(HERE/'fixture.stderr') == command['stderrSHA256']
assert sha(HERE/'copied-source-manifest.json') == command['sourceManifestSHA256']
arithmetic = load(HERE/'arithmetic.json')
assert arithmetic['planningCreditsLowerBound'] == 128*39432+64*39368 == 7566848
assert arithmetic['planningCreditsUpperBoundIncludingUncommittedTerminalPlan'] == 7571072
assert arithmetic['lookupCreditsLowerBound'] == 3*280175+66*39433 == 3443103
assert arithmetic['lookupCreditsUpperBound'] == 129*(280175+39433) == 41229432
assert arithmetic['decodeAndPolicyCreditsLowerBound'] == 64000000-640-7571072-41229432 == 15198856
assert arithmetic['decodeAndPolicyCreditsUpperBound'] == 64000000-640-7566848-3443103 == 52989409
assert not arithmetic['repeatedCompletedDecodesProvableFromAggregates']
binding = load(ROOT/'verification/swift-exact-reactor-after-cache-root-selection/result-binding.json')
assert binding['integrityVerified'] and binding['targetAttempts'] == 1
assert sha(ROOT/'verification/swift-exact-reactor-after-cache/result-seal.json') == binding['sealSHA256']
cleanup = load(HERE/'cleanup.json')
assert cleanup['ownedPathsAbsent'] and cleanup['live132SourceHashesUnchanged'] and cleanup['inputHashesUnchanged']
assert cleanup['processGroupMembers'] == [] and cleanup['signalsSent'] == []
assert all(not (HERE/name).exists() for name in ('scratch','target','tmp'))
proposal = load(HERE/'instrumentation-proposal.json')
assert proposal['targetAttemptsSelectedByThisPacket'] == 0 and not proposal['targetExecutedByThisPacket']
assert proposal['fixedState']['completedDecodeSeenBitmapBytes'] == 10000
assert 34+79832 < proposal['fixedState']['completedDecodeSeenBitmapAbsoluteIndexCapacity']
assert not proposal['fixedState']['dynamicPerFunctionMap']
receipt = load(HERE/'receipt.json')
assert receipt['fixturePassed'] and not receipt['targetExecuted'] and not receipt['liveVMChanged']
assert not receipt['targetCPUAttribution'] and not receipt['targetStageAttribution']
print(f"Verified {len(seal['files'])} packet files, input hashes, 132 live source hashes, bounded fixture and source arithmetic; no compile or guest execution.")
