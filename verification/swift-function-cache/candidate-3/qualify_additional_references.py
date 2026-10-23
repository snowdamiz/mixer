#!/usr/bin/env python3
"""Complete the two explicitly ignored table-memory references omitted from the initial group."""
import hashlib,json,os,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
base=json.loads((HERE/'qualification/regressions.json').read_text());assert base['status']=='pass'
source=base['source_manifest']
def unchanged():return all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in source.items())
ENV=dict(os.environ);ENV['PATH']='/opt/homebrew/opt/rustup/bin:'+ENV.get('PATH','');ENV['CARGO_TARGET_DIR']='/tmp/mixer-cache-candidate3-regressions-target'
r={'scope':'two original table-memory development Node reference tests; no Swift target invocation','source_manifest':source,'source_manifest_sha256':base['source_manifest_sha256'],'prior_reference_tests_per_mode':7,'commands':[]}
for release in [False,True]:
 assert unchanged()
 args=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-swift-reactor,experimental-span-execution','--test','table_memory_differential']
 if release:args+=['--release']
 args+=['--','--ignored','--nocapture'];start=time.monotonic();p=subprocess.run(args,cwd=ROOT,env=ENV,text=True,capture_output=True)
 c={'argv':args,'cwd':str(ROOT),'CARGO_TARGET_DIR':ENV['CARGO_TARGET_DIR'],'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.monotonic()-start}
 c['exactly_two_passed']=bool(re.search(r'^test result: ok\. 2 passed; 0 failed; 0 ignored;',p.stdout,re.M));r['commands'].append(c)
 assert p.returncode==0 and c['exactly_two_passed'] and unchanged()
 print(json.dumps({'argv':args,'passed':2,'seconds':c['seconds']}),flush=True)
r['status']='pass';(HERE/'qualification/additional-reference-receipt.json').write_text(json.dumps(r,indent=2)+'\n')
