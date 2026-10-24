#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
import collect as c

def build(features,profile):
 vm=c.source('candidate');name='runtime-'+features+'-'+profile;t=c.target(vm,features,profile,'runtime');env={'CARGO_TARGET_DIR':str(t)}
 flags=['--features','experimental-swift-reactor']if features=='swift'else['--all-features']if features=='all'else[]
 a=['cargo','test','--lib','--no-run','--offline','--locked',*flags,*(['--release']if profile=='release'else[]),'--message-format=json-render-diagnostics']
 p,_=c.command('build-'+name,a,vm,env);rows=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')];selected=[x for x in rows if x.get('reason')=='compiler-artifact'and x.get('executable')and x['profile']['test']and x['target']['name']=='mixer_vm'and x['target']['src_path'].endswith('/src/lib.rs')];assert len(selected)==1 and selected[0]['fresh']is False
 output,record=c.retain_and_run(name,selected[0],vm,env,args=['--nocapture','--test-threads=1']);text=output.stdout.decode();m=re.search(r'test result: ok\. (\d+) passed; 0 failed;',text);assert m,(name,text[-3000:])
 tests=json.loads((c.HERE/'artifacts'/name/'test-list.json').read_text());host=[x for x in tests if'::host_tests::h'in x]
 assert len(host)==(0 if features=='default'else16),(name,host)
 record.update(features=features,profile=profile,passed=int(m[1]),hostTests=len(host),fullLibrarySuite=True);c.save('runtime-'+features+'-'+profile+'.json',record)
 return record

def main():
 vm=c.source('candidate');expected=c.digest(json.loads((c.HERE/'candidate-source-manifest.json').read_text()));assert c.digest(c.manifest(vm))==expected
 layouts=json.loads((c.HERE/'accounted-layouts.json').read_text());assert len(layouts)==16
 for x in layouts:
  assert x['cargoArtifactFresh']is False and x['targetCreatedEmpty']
 for config in['production','unit']:
  receipt=json.loads((c.HERE/'commands'/('final-corrected-mir-'+config)/'receipt.json').read_text());assert receipt['sourceTreeBeforeSHA256']==expected
 rows=[]
 for f in['swift','all','default']:
  for p in['debug','release']:
   rows.append(build(f,p));c.save('runtime-results.json',rows)
 print('Qualified',sum(x['passed']for x in rows),'actual library test executions in six isolated contexts')
if __name__=='__main__':main()
