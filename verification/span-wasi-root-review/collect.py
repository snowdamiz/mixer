#!/usr/bin/env python3
"""Root combined-feature verification; no published profile or ABI changes."""
import argparse, datetime, hashlib, json, os, pathlib, subprocess, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--name',required=True)
name=parser.parse_args().name
assert name and all(c.isalnum() or c=='-' for c in name)
OUT=pathlib.Path(__file__).resolve().parent/name
OUT.mkdir(exist_ok=False)
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR='/tmp/mixer-root-span-wasi-target')
def digest(data):return hashlib.sha256(data).hexdigest()
def sources():
 paths=[ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']
 for base in ['vm/src','vm/tests','vm/tools']:
  paths.extend(p for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 return {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sorted(paths)}
receipt={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':[],'scope':'Combined host feature regression, allocation/denial/differential tests only. No full Swift reactor admission or execution, native archive change, phone, release or GA qualification.'}
commands=[('rust-version',['rustc','--version','--verbose']),('cargo-version',['cargo','--version']),('node-version',['node','--version'])]
for mode in ['debug','release']:
 flags=[] if mode=='debug' else ['--release']
 commands.append((mode,['cargo','test','--locked','--manifest-path','vm/Cargo.toml',*flags,'--all-features']))
 commands.append((mode+'-oracles',['cargo','test','--locked','--manifest-path','vm/Cargo.toml',*flags,'--all-features','--','--ignored']))
commands += [('focused-clippy',['cargo','clippy','--locked','--manifest-path','vm/Cargo.toml','--all-features','--lib','--bins','--test','span_execution','--test','span_execution_allocations','--test','span_execution_oracle','--test','swift_wasi','--test','swift_wasi_allocations','--','-D','warnings']),('format',['cargo','fmt','--manifest-path','vm/Cargo.toml','--check'])]
failed=False
for label,argv in commands:
 before=sources(); started=time.monotonic(); result=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600);after=sources()
 (OUT/(label+'.log')).write_bytes(result.stdout)
 for manifest in [before,after]:
  raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode();(OUT/('source-'+digest(raw)+'.json')).write_bytes(raw)
 item={'label':label,'argv':argv,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,'log':label+'.log','log_sha256':digest(result.stdout),'source_before':digest((json.dumps(before,sort_keys=True,indent=2)+'\n').encode()),'source_after':digest((json.dumps(after,sort_keys=True,indent=2)+'\n').encode()),'source_stable':before==after}
 receipt['commands'].append(item);failed|=result.returncode!=0 or before!=after
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(label,result.returncode,'stable',before==after,flush=True)
receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['passed']=not failed
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(1 if failed else 0)
