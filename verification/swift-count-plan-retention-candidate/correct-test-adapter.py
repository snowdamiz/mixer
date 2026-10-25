#!/usr/bin/env python3
import json,pathlib
out=pathlib.Path(__file__).resolve().parent
p=out/'.scratch/candidate/src/experimental_swift_reactor/cache.rs';s=p.read_text()
assert s.count('            counts.test_changed_instructions(),')==1
s=s.replace('            counts.test_changed_instructions(),','            SwiftMode::scan_counts(&counts).test_changed_instructions(),',1);p.write_text(s)
(out/'test-adapter-correction.json').write_text(json.dumps({'failure':'commands/candidate-original-swift/stderr',
  'scope':'Existing cfg(test) count_build_mismatch helper now extracts Counts from the new outer scan outcome before retaining its intentionally wrong instruction count.',
  'productionPolicyChanged':False,'existingAssertionRemoved':False},indent=2)+'\n')
