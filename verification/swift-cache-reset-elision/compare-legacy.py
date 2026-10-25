#!/usr/bin/env python3
"""Compare complete retained frozen legacy trace observations across feature/mode contexts."""
from pathlib import Path
import hashlib,json,re
out=Path(__file__).resolve().parent
name='experimental::cache::tests::frozen_layout_and_trace_observation'
traces={};allocations={}
for label in ('compatibility-debug','compatibility-release','all-features-debug','all-features-release'):
 source=out/f'matrix-{label}.stdout';s=source.read_text();m=re.search(r'^test '+re.escape(name)+r' \.\.\. ',s,re.M);assert m,label
 rest=s[m.end():];next_test=re.search(r'^test ',rest,re.M);block=rest[:next_test.start()] if next_test else rest
 assert block.rstrip().endswith('ok'),label
 lines=block.strip().splitlines();allocation=[line for line in lines if line.startswith('allocation ')]
 common='\n'.join(line for line in lines if not line.startswith('allocation '))+'\n'
 traces[label]=common;allocations[label]=allocation
 (out/f'legacy-{label}.trace').write_text(common)
assert len(set(traces.values()))==1
assert allocations['all-features-debug']==allocations['all-features-release']
assert len(allocations['all-features-debug'])==4
(out/'legacy-comparison.json').write_text(json.dumps({'commonTraceIdenticalAcrossFourContexts':True,'commonTraceSHA256':hashlib.sha256(next(iter(traces.values())).encode()).hexdigest(),'contexts':list(traces),'linesPerCommonTrace':len(next(iter(traces.values())).splitlines()),'allFeatureAllocationObservationsIdenticalDebugRelease':True,'allFeatureAllocationObservations':allocations['all-features-debug'],'excludedLinesFromFeatureOnlyComparison':'Only the four cfg(experimental-swift-reactor) allocation-observer lines, separately retained and compared Debug/Release'},sort_keys=True,indent=2)+'\n')
print((out/'legacy-comparison.json').read_text())
