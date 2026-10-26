#!/usr/bin/env python3
"""Run this packet's own source tools only; preserve attempts and all outputs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
dest=HERE/'commands'/stamp;dest.mkdir(parents=True)
rows=[]
for label,args in [('prepare',['-B','prepare.py']),('model',['-B','model.py']),('normal',['-B','check.py']),('optimized',['-O','-B','check.py'])]:
 argv=[sys.executable,*args[:-1],str(HERE/args[-1])]
 p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
 (dest/(label+'.stdout')).write_text(p.stdout);(dest/(label+'.stderr')).write_text(p.stderr)
 row={'label':label,'argv':argv,'cwd':str(ROOT),'exit_code':p.returncode,'stdout_sha256':sha(p.stdout.encode()),'stderr_sha256':sha(p.stderr.encode()),'script_sha256':sha((HERE/args[-1]).read_bytes())};rows.append(row)
 print(label,p.returncode,p.stdout[:400].strip())
 if p.returncode:break
library=[]
for name in ('analyzer.rs','cache_state.rs','envelope.rs'):
 p=ROOT/'verification/swift-cache-state-implementation/correction-3/source/library'/name;b=p.read_bytes();library.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
receipt={'started_at':stamp,'completed_at':datetime.now(timezone.utc).isoformat(),'python':sys.version,'python_executable':sys.executable,'source_sha256':sha((ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_bytes()),'source_tree_scope':'three frozen library files; not a new complete candidate/tree replay','library_source_members':library,'library_source_tree_digest':sha(json.dumps(library,separators=(',',':')).encode()),'candidate_revision_identity_seal_sha256':sha((ROOT/'verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json').read_bytes()),'full_candidate_source_tree_digest_inherited_from_selected_review':'45bd39ce40ce25cba9304dfd014d8ad3da1b9ee83f9e55de91618da8b77d7dac','command_scope':'only owned Python standard-library source models/checks; no product/compiler/runtime/native/capture/process/Git/hosted execution','commands':rows,'all_passed':len(rows)==4 and all(r['exit_code']==0 for r in rows)}
(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(HERE/'latest-run.json').write_text(json.dumps({'path':str(dest.relative_to(ROOT)),'receipt_sha256':sha((dest/'receipt.json').read_bytes())},indent=2)+'\n')
if not receipt['all_passed']:raise SystemExit(1)
