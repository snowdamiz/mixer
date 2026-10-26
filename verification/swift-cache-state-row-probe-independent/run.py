#!/usr/bin/env python3
import datetime,hashlib,json,pathlib,subprocess,sys
D=pathlib.Path(__file__).resolve().parent
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=D/'commands'/stamp;out.mkdir(parents=True)
rows=[]
for label,args in [('normal',[sys.executable,'-B',str(D/'check.py')]),('optimized',[sys.executable,'-B','-O',str(D/'check.py')])]:
 p=subprocess.run(args,cwd=D.parents[1],capture_output=True)
 (out/(label+'.stdout')).write_bytes(p.stdout);(out/(label+'.stderr')).write_bytes(p.stderr)
 row={'label':label,'command':args,'exit':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()};rows.append(row)
 print(json.dumps(row))
 if p.returncode:break
receipt={'schema':1,'python':sys.version,'executable':sys.executable,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checker_sha256':hashlib.sha256((D/'check.py').read_bytes()).hexdigest(),'commands':rows,'scope':'source and independent offline Python model only; no producer executable/import, Rust/compiler/native/runtime/UI/capture/process inventory/Git/hosted harness'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(D/'latest-run.json').write_text(json.dumps({'path':str(out.relative_to(D))},indent=2)+'\n')
sys.exit(rows[-1]['exit'])
