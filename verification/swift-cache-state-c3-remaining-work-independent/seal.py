#!/usr/bin/env python3
"""Seal only the independently owned review directory."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    rows=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p.name=='seal.json':continue
        b=p.read_bytes();rows.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
    seal={'schema':1,'status':'independent bounded source correction; root selection required',
      'members':rows,'bytes':sum(r['bytes'] for r in rows),
      'source_sha256':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
      'producer_seal_sha256':'90eb895fe6c34dc68c3bb7826b0852f49926375f80c510020f4f7ed454ad8cb3',
      'root_selection_required':True,'producer_original_completeness_accepted':False,
      'corrected_components_source_qualified':True,'combined_all_work_or_implementation_accepted':False,
      'native_runtime_or_capture_executed':False,'GA_qualified':False}
    path=HERE/'seal.json'
    if '--verify' in sys.argv:
        if json.loads(path.read_text())!=seal:raise ValueError('independent seal drift')
    else:path.write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps({'verified':'--verify' in sys.argv,'seal_sha256':sha(path.read_bytes()),
      'members':len(rows),'bytes':seal['bytes']}))

if __name__=='__main__':main()
