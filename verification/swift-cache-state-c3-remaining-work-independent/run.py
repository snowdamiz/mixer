#!/usr/bin/env python3
"""Run only this independent source checker; retain both interpreter modes."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    started=datetime.now(timezone.utc).isoformat()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=HERE/'commands'/stamp;output.mkdir(parents=True)
    commands=[];parsed={}
    for mode,flags in [('normal',['-B']),('optimized',['-B','-O'])]:
        argv=[sys.executable,*flags,str(HERE/'review.py')]
        if mode=='normal':argv.append('--write')
        r=subprocess.run(argv,cwd=ROOT,capture_output=True)
        (output/f'{mode}.stdout').write_bytes(r.stdout)
        (output/f'{mode}.stderr').write_bytes(r.stderr)
        commands.append({'mode':mode,'argv':argv,'cwd':str(ROOT),'returncode':r.returncode,
          'stdout':str((output/f'{mode}.stdout').relative_to(ROOT)),
          'stderr':str((output/f'{mode}.stderr').relative_to(ROOT)),
          'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),
          'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()})
        if r.returncode==0:parsed[mode]=json.loads(r.stdout)
    equivalent=False
    if len(parsed)==2:
        a=dict(parsed['normal']);b=dict(parsed['optimized']);a.pop('optimized');b.pop('optimized')
        equivalent=a==b
    receipt={'schema':1,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),
      'python':sys.version,'executable':sys.executable,
      'scope':'independent source/model/data only; no producer scripts imported/executed',
      'source_sha256':sha(ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs'),
      'source_tree_digest':parsed.get('normal',{}).get('custody',{}).get('candidate_source_tree_digest'),
      'review_sha256':sha(HERE/'review.py'),'coverage_sha256':sha(HERE/'coverage.json'),
      'runner_sha256':sha(HERE/'run.py'),'commands':commands,'normal_optimized_equivalent':equivalent,
      'passed':equivalent and all(c['returncode']==0 for c in commands),
      'errors':[c for c in commands if c['returncode']!=0],
      'product_compiler_Rust_fixture_native_UI_capture_process_inventory_Git_hosted_actions':False,
      'implementation_accepted':False,'GA_qualified':False}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (HERE/'latest-run.json').write_text(json.dumps({'receipt':str((output/'receipt.json').relative_to(ROOT))},indent=2)+'\n')
    print(json.dumps({'passed':receipt['passed'],'normal_optimized_equivalent':equivalent,
      'receipt':str((output/'receipt.json').relative_to(ROOT)),
      'mutation_controls_each_mode':len(parsed.get('normal',{}).get('mutation_controls_rejected',[]))}))
    if not receipt['passed']:raise SystemExit(1)
    subprocess.run([sys.executable,'-B',str(HERE/'seal.py')],cwd=ROOT,check=True)

if __name__=='__main__':main()
