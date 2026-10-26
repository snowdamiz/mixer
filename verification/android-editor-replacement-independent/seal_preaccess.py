#!/usr/bin/env python3
"""Freeze only this correction review's preaccess source and custody evidence."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
receipt=json.loads((HERE/'preaccess-receipt.json').read_text())
assert receipt['control_compilation_passed']
assert receipt['active_correction_candidate_reads']==0
assert receipt['active_correction_candidate_executions']==0
assert receipt['baseline_or_correction_product_method_invocations']==0
assert receipt['prior_audit_members_verified_unchanged']==1046
sealpath=HERE/'preaccess-seal.json'
rows=[]
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or path==sealpath:continue
    assert not path.is_symlink();data=path.read_bytes()
    rows.append({'path':path.relative_to(HERE).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
seal={'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),
      'scope':'Independent correction actual-source control preparation and type-compile only; no candidate access/product execution',
      'members':rows,'candidate_reads':0,'candidate_executions':0,'product_method_invocations':0,
      'behavioral_status':'all_pending_root_frozen_release','native_or_GA_accepted':False}
sealpath.write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'members':len(rows),'bytes':sum(row['bytes'] for row in rows),
                  'seal_sha256':hashlib.sha256(sealpath.read_bytes()).hexdigest(),
                  'candidate_reads':0,'candidate_executions':0,'product_method_invocations':0}))
