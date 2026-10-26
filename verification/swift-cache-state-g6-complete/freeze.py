#!/usr/bin/env python3
"""Seal only this lane; no execution of product/compiler/native code."""
import json
from pathlib import Path
import sys
from datetime import datetime,timezone
import ledger

HERE=Path(__file__).resolve().parent
members=[ledger.info(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='seal.json']
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),
      'status':'producer complete conservative G6 component-source bound for exact selected source; independent review pending; no implementation or lifetime acceptance',
      'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,
      'source_sha256':ledger.SOURCE_SHA,'owned_scope':['verification/swift-cache-state-g6-complete/**'],
      'members':members,'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members)}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal_sha256':ledger.digest((HERE/'seal.json').read_bytes()),'member_count':len(members),'member_bytes':seal['member_bytes']},indent=2))
