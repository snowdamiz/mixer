#!/usr/bin/env python3
from pathlib import Path
import datetime
import hashlib
import json

D = Path(__file__).resolve().parent
out = D / 'preaccess-seal.json'
if out.exists():
    raise SystemExit('Already frozen; retain this packet unchanged')
members = []
for path in sorted(D.rglob('*')):
    if not path.is_file() or path == out:
        continue
    data = path.read_bytes()
    members.append({'path': str(path.relative_to(D)), 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()})
result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Independent prospective preaccess controls with complete old-source-only typecheck/baselines',
          'active_implementation_access': False,
          'selected_candidate_execution_or_acceptance': False,
          'native_OTA_GA_accepted': False, 'members': members,
          'member_count': len(members), 'member_bytes': sum(item['bytes'] for item in members)}
out.write_text(json.dumps(result, indent=2) + '\n')
print(hashlib.sha256(out.read_bytes()).hexdigest(), len(members), result['member_bytes'])
