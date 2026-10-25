#!/usr/bin/env python3
"""Update only copied historical Swift work/policy snapshots for charged SLRU."""
from pathlib import Path
import difflib,json
H=Path(__file__).resolve().parent
p=H/'candidate/src/experimental_swift_reactor/cache_tests.rs'
before=p.read_text();s=before
changes=[
('assert_eq!(c.usage(None).cache_work, 4_928);','assert_eq!(c.usage(None).cache_work, 4_928 + 64); // admitted tier initialization'),
('assert_eq!(hit.stage_work.iter().sum::<u64>(), 8);','assert_eq!(hit.stage_work.iter().sum::<u64>(), 8 + 1 + 2 * 64 + 1); // first promotion'),
('\\\"constructorWork\\\":4928','\\\"constructorWork\\\":4992'),
('\\\"hitWork\\\":8,\\\"hitStages','\\\"hitWork\\\":138,\\\"hitStages'),
('\\\"case\\\":\\\"lru\\\"','\\\"case\\\":\\\"slru\\\"'),
('''    assert_eq!(cache.usage().hits, 3);
    assert_eq!(cache.usage().misses, 5);
    assert_eq!(cache.usage().evictions, 2);''','''    // SLRU retains twice-pinned35 and evicts probationary37 in this trace.
    // The unchanged baseline retains the original LRU 3/5/2 expectations.
    assert_eq!(cache.usage().hits, 2);
    assert_eq!(cache.usage().misses, 6);
    assert_eq!(cache.usage().evictions, 3);'''),
('assert_eq!(hit_work, 260); // two ordinary headers plus hash/head plus4*64 nodes.','assert_eq!(hit_work, 260 + 1 + 2 * 64 + 1); // original chain + tier/scan/promotion')]
for old,new in changes:
 assert s.count(old)==1,(old,s.count(old))
 s=s.replace(old,new)
p.write_text(s)
(H/'historical-snapshot-adjustments.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='initial-candidate-snapshots',tofile='charged-slru-snapshots')))
(H/'historical-snapshot-adjustments.json').write_text(json.dumps({'schema':1,'failedCommand':'candidate-cache-release','productSourceChanged':False,'changes':'Explicitly charged constructor and first-promotion work; observed SLRU outcomes in historical reset-elision LRU trace. No original baseline snapshot changed.','firstHitExtraCredits':'1 tier + 2*64 occupied/tier + 0 protected ages + 1 promotion write = 130','chain64Work':'260 + 130 = 390'},indent=2)+'\n')
print(json.dumps({'adjustments':len(changes)}))
