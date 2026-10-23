#!/usr/bin/env python3
"""Include the first layout line sharing the single-thread harness prefix."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
receipt=json.loads((HERE/'independent-legacy.json').read_text())
pattern=re.compile(r'^(layout |offsets |scratch |new |miss |hit |release |invalid |cancel |allocation |precedence |eviction prefix )')
comparisons=[]
for i in range(0,len(receipt['commands']),2):
    observations=[]
    for command in receipt['commands'][i:i+2]:
        data=(HERE/command['output']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==command['output_sha256']
        lines=[]
        for line in data.decode().splitlines():
            if line.startswith('test ') and ' ... ' in line:line=line.split(' ... ',1)[1]
            if pattern.match(line):lines.append(line)
        observations.append(lines)
    assert observations[0]==observations[1]
    comparison=receipt['comparisons'][i//2]|{'exact_lines':len(lines),'observations_sha256':hashlib.sha256('\n'.join(lines).encode()).hexdigest()}
    assert comparison['exact_lines'] in [122,126]
    comparisons.append(comparison)
result={'scope':'same eight independent command logs, with only the harness test-name prefix removed from first layout line','initial_receipt_sha256':hashlib.sha256((HERE/'independent-legacy.json').read_bytes()).hexdigest(),'comparisons':comparisons}
(HERE/'independent-legacy-normalized.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(comparisons,indent=2))
