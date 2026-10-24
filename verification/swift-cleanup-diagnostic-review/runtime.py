#!/usr/bin/env python3
import json,re,sys
import collect as c

def build(features,profile,attempt='qualified'):
 vm=c.source('candidate');qualified=json.loads((c.HERE/'accounting-qualification.json').read_text());assert c.digest(c.manifest(vm))==qualified['sourceSHA256']
 name=attempt+'-runtime-'+features+'-'+profile;t=c.target(vm,features,profile,name);env={'CARGO_TARGET_DIR':str(t)}
 flags=['--features','experimental-swift-reactor']if features=='swift'else['--all-features']if features=='all'else[]
 argv=['cargo','test','--lib','--no-run','--offline','--locked',*flags,*(['--release']if profile=='release'else[]),'--message-format=json-render-diagnostics']
 p,_=c.command('build-'+name,argv,vm,env);rows=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')]
 artifacts=[x for x in rows if x.get('reason')=='compiler-artifact'and x.get('executable')and x['profile']['test']and x['target']['name']=='mixer_vm'and x['target']['src_path'].endswith('/src/lib.rs')];assert len(artifacts)==1 and artifacts[0]['fresh']is False
 output,record=c.retain_and_run(name,artifacts[0],vm,env,args=['--nocapture','--test-threads=1'],probe_args=['cdr','--nocapture','--test-threads=1']if features!='default'else None)
 text=output.stdout.decode();m=re.search(r'test result: ok\. (\d+) passed; 0 failed;',text);assert m
 tests=json.loads((c.HERE/'artifacts'/name/'test-list.json').read_text());selected=[x for x in tests if'::cdr'in x]
 record.update(features=features,profile=profile,passed=int(m[1]),selectedTests=selected,fullLibrarySuite=True);c.save(name+'.json',record)
 return record
if __name__=='__main__':
 for f in ['swift','all']:
  for p in ['debug','release']:build(f,p,sys.argv[1]if len(sys.argv)>1 else'qualified')
