"""Externally sealed ordinary-host offline source/command join, not admission."""
from pathlib import Path
import argparse,datetime,hashlib,json,platform,signal,sys,time
BASE=Path(__file__).resolve().parent
REPO=BASE.parents[3]
MANIFEST_SHA256='62c540b9f8f610918ccd5dbab598bb463875584f72530955241f41ab0bc2e0f4'
def ident(p):
 d=p.read_bytes();return {'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def verify(sha):
 assert ident(BASE/'seal.json')['sha256']==sha,'external source seal'
 seal=json.loads((BASE/'seal.json').read_bytes());assert {str(p.relative_to(BASE))for p in BASE.rglob('*')if p.is_file()}=={'seal.json'}|{x['path']for x in seal['members']}
 for x in seal['members']:assert ident(BASE/x['path'])=={k:x[k]for k in('bytes','sha256')}
 assert ident(BASE/'input-manifest.json')['sha256']==MANIFEST_SHA256
 manifest=json.loads((BASE/'input-manifest.json').read_bytes())
 for root in manifest['closed_roots']:
  paths=list((REPO/root['root']).rglob('*'));assert not any(p.is_symlink()for p in paths);assert {str(p.relative_to(REPO))for p in paths if p.is_file()}==set(root['paths'])
 for x in manifest['files']:
  p=Path(x['path']);assert not p.is_absolute()and'..'not in p.parts;assert ident(REPO/p)=={k:x[k]for k in('bytes','sha256')}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-seal-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();assert out.is_relative_to(BASE.parent)and not out.is_relative_to(BASE)and not out.exists();out.mkdir();entry=exit=False;status='failed';start=time.monotonic()
 try:
  signal.alarm(60);verify(a.source_seal_sha256);entry=True;sys.path.insert(0,str(BASE/'code'))
  from test_join_original98 import controls
  from join_original98 import load_inputs,validate
  results=controls();save(out/'fresh-controls.json',results);save(out/'original98-joined.json',validate(load_inputs()));status='passed-offline98-commands99-aliases-source-receipt-join; not-qualified';print(json.dumps({'status':status,'actual_commands':98,'historical_aliases':99,'refusals':len(results['refusal_controls'])}),flush=True)
 finally:
  signal.alarm(60)
  try:verify(a.source_seal_sha256);exit=True
  finally:
   signal.alarm(0);save(out/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'source_seal_sha256':a.source_seal_sha256,'manifest_sha256':MANIFEST_SHA256,'closure_entry_verified':entry,'closure_exit_verified':exit,'argv':sys.argv,'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),'elapsed_seconds':time.monotonic()-start,'maximum_parent_seconds':60,'children_started':0,'Java_reexecuted':False,'trusted_runtime_boundary':'Ordinary caller-selected local Python/OS. No interpreter or v5 execution closure claim.','qualified':False})
if __name__=='__main__':main()
