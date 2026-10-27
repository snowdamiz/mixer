#!/usr/bin/env python3
"""Independent host-only frozen input review. Does not run frozen recorders."""
from pathlib import Path
import contextlib, datetime, hashlib, importlib.util, io, json, os, platform, sys, time, unittest
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PROVIDER=ROOT/'verification/swift-guarded-snapshot-owned-binding-provider'
BASE=ROOT/'verification/swift-guarded-snapshot-scoped-binding-source'
PROFILE='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def write(name,obj): (HERE/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def row(path):
 d=path.read_bytes(); return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(d),'sha256':sha(d)}
def frozen(path,expected,count):
 d=(path/'seal.json').read_bytes(); assert sha(d)==expected
 seal=json.loads(d); assert seal['member_count']==len(seal['members'])==count
 for r in seal['members']:
  d=(path/r['path']).read_bytes(); assert (len(d),sha(d))==(r['bytes'],r['sha256']),r['path']
 assert sum(r['bytes'] for r in seal['members'])==seal['member_bytes']
 assert sha(canonical(seal['members']))==seal['tree_sha256']
 return seal

def main():
 started=datetime.datetime.now(datetime.timezone.utc).isoformat(); begin=time.monotonic()
 out=io.StringIO(); error=None; result=None
 try:
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
   p=frozen(PROVIDER,'7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de',50)
   b=frozen(BASE,'84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2',200)
   release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-owned-binding-provider-frozen-release.json'
   assert sha(release.read_bytes())=='d298461d91895f8333ae11ee9bb1b5c274e955a3589a1a2b5c75c0c329e2426b'
   assert json.loads(release.read_bytes())['accepted'] is False
   custody=json.loads((PROVIDER/'proposed-source-custody.json').read_bytes())
   rows=[]
   for r in custody:
    d=(ROOT/r['origin']).read_bytes(); assert (len(d),sha(d))==(r['bytes'],r['sha256'])
    rows.append({k:r[k] for k in ('path','bytes','sha256')})
   assert len(rows)==146
   assert sha(canonical(rows))=='acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
   old=json.loads((BASE/'source-manifest.json').read_bytes())['members']
   assert len(old)==146
   changed=[r['path'] for r,s in zip(rows,old) if r!=s]
   assert changed==[PROFILE]
   fragment=(PROVIDER/'existing-owner-candidate.inc.rs').read_bytes()
   insert=b'\n// Isolated unqualified existing-owner preparation proposal.\n'+fragment+b'\n'
   source=(PROVIDER/'proposed-overlay/vm'/PROFILE).read_bytes()
   base=(BASE/'source/vm'/PROFILE).read_bytes()
   assert source==base[:-4]+insert+base[-4:]
   actual=ROOT/'verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm'
   assert (len(actual.read_bytes()),sha(actual.read_bytes()))==(1947,'9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806')
   host=json.loads((ROOT/'verification/swift-guarded-snapshot-host-composition/host-support-manifest.json').read_bytes())
   assert len(host['members'])==11
   for r in host['members']:
    d=(ROOT/'verification/swift-real-profile-loader-binding/host'/r['path']).read_bytes()
    assert (len(d),sha(d))==(r['bytes'],r['sha256'])
   write('input-custody.json',{'provider_seal':row(PROVIDER/'seal.json'),'base_seal':row(BASE/'seal.json'),'root_release':row(release),'candidate_source_custody':custody,'host11_manifest':host,'source':row(actual),'candidate_source_members':146,'unchanged_source_members':145,'changed_source_members':changed})
   sys.path.insert(0,str(PROVIDER))
   spec=importlib.util.spec_from_file_location('provider_tests',PROVIDER/'test_input_model.py'); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
   suite=unittest.defaultTestLoader.loadTestsFromModule(module)
   result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
   assert result.testsRun==18 and result.wasSuccessful() and not result.skipped
   # Independently rehash all frozen inputs after tests: no producer recorder run.
   frozen(PROVIDER,'7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de',50)
   frozen(BASE,'84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2',200)
 except BaseException as e:
  import traceback; error=repr(e); traceback.print_exc(file=out)
 data=out.getvalue().encode(); (HERE/'host.stdout').write_bytes(data); (HERE/'host.stderr').write_text(error or '')
 receipt={'schema':1,'started_at':started,'elapsed_seconds':time.monotonic()-begin,'argv':[sys.executable,*sys.argv],'cwd':os.getcwd(),'python_version':sys.version,'python_executable':row(Path(sys.executable).resolve()) if Path(sys.executable).resolve().is_relative_to(ROOT) else {'path':str(Path(sys.executable).resolve()),'sha256':sha(Path(sys.executable).resolve().read_bytes())},'platform':platform.platform(),'runner_sha256':sha(Path(__file__).read_bytes()),'tests_run':None if result is None else result.testsRun,'failures':None if result is None else len(result.failures),'errors':None if result is None else len(result.errors),'skipped':None if result is None else len(result.skipped),'exception':error,'exit_code':0 if error is None else 1,'stdout_sha256':sha(data),'frozen_inputs_unchanged':error is None,'scope':'Fresh in-process Python byte/format oracle and immutable custody, not product Rust behavior','compiler_invocations':0,'native_runtime_UI_capture_or_global_process_inventory':False,'product_or_loader_execution':False,'operational_grant':False,'all_three_selectors':'Pending','GA':False}
 write('host-replay-receipt.json',receipt); print(json.dumps(receipt)); return receipt['exit_code']
if __name__=='__main__': raise SystemExit(main())
