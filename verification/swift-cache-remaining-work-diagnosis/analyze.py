#!/usr/bin/env python3
"""Read-only inputs, source-derived bounds and finite fixture assertions."""
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
load = lambda p: json.loads(Path(p).read_text())
snapshots = load(ROOT/'verification/swift-exact-reactor-after-cache/phase-counters.json')['snapshots']
first, initialized, terminal = snapshots
cache = terminal['cache']
hits, misses, decodes, evictions = [cache[k] for k in ('hits','misses','decodes','evictions')]
assert (hits, misses, decodes, evictions) == (280175,39433,39432,39368)
slots = 64
planning_min = 2*slots*decodes + slots*evictions
planning_max = planning_min + 2*slots + slots*slots
lookup_min = 3*hits + (slots+2)*misses
lookup_max = (1+slots+slots)*(hits+misses)
rows = load(HERE/'fixture-observations.json')['observations']
assert len(rows) == 9
assert [r.get('work') for r in rows[:-1]] == [205,3,286,3,15335,66,129,30888]
for row in rows[:-1]:
    assert sum(row['stages']) == row['work']
    assert row['stages'][2] == row['stages'][4] == 0
# Exact complete-body source formula; no target-body parsing or target execution.
def body_credits(B, I, P=0, G=0, L=0, C=0, A=0, T=0):
    return 4 + 2*P + 2*B + 2*G + 3*L + 3*I + 5*C + 3*A + 3*T
assert body_credits(2,1) == 11
assert body_credits(17,12,C=3,A=1) == 92
assert 66+128+body_credits(2,1) == rows[0]['work']
assert 66+128+body_credits(17,12,C=3,A=1) == rows[2]['work']
value = {
    'schema': 1, 'scope': 'arithmetic bounds from sealed counters and current source; not measured target stage/CPU attribution',
    'targetCounters': dict(hits=hits, misses=misses, completedDecodes=decodes, evictions=evictions),
    'pinAttemptsCountedAsHitOrMiss': hits+misses,
    'hitFractionOfCountedPins': hits/(hits+misses),
    'planningCreditsLowerBound': planning_min,
    'planningCreditsUpperBoundIncludingUncommittedTerminalPlan': planning_max,
    'planningLowerBoundFractionOf64000000': planning_min/64000000,
    'lookupCreditsLowerBound': lookup_min, 'lookupCreditsUpperBound': lookup_max,
    'decodeAndPolicyCreditsLowerBound': 64000000-640-planning_max-lookup_max,
    'decodeAndPolicyCreditsUpperBound': 64000000-640-planning_min-lookup_min,
    'repeatedCompletedDecodesProvableFromAggregates': False,
    'definedFunctions': 79832,
    'completedDecodeExcessOverDefinedFunctions': max(0, decodes-79832),
    'cacheBytesLimit': 16*1024*1024,
    'sumOfObservedResidentConstructionAndFixedPeaks': cache['peak_resident_bytes']+cache['peak_construction_bytes']+cache['fixed_reserved'],
    'successfulCompleteDecodeFormula': '4+2P+2B+2G+3L+3I+5C+3A+3T',
    'formulaFlat': body_credits(2,1), 'formulaNested': body_credits(17,12,C=3,A=1),
    'initializeToCorpus1': {
        'completedDecodes': decodes-initialized['cache']['decodes'],
        'cacheCredits': terminal['work']['cache_work']-initialized['work']['cache_work'],
    },
}
(HERE/'arithmetic.json').write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
print(json.dumps(value, sort_keys=True))
