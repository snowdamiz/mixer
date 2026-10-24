#!/usr/bin/env python3
import collect as c
import json,re

def main():
 records=[]
 for label in['baseline','candidate']:
  vm=c.source(label)
  for profile in['debug','release']:
   name='qualified-frozen-'+label+'-'+profile;t=c.target(vm,'all',profile,'qualified-frozen-runtime');env={'CARGO_TARGET_DIR':str(t)}
   p,_=c.command('build-'+name,['cargo','test','--test','span_execution','--no-run','--all-features','--offline','--locked',*(['--release']if profile=='release'else[]),'--message-format=json-render-diagnostics'],vm,env)
   rows=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')];a=[x for x in rows if x.get('reason')=='compiler-artifact'and x.get('executable')and x['target']['name']=='span_execution'and'test'in x['target']['kind']];assert len(a)==1 and a[0]['fresh']is False
   output,record=c.retain_and_run(name,a[0],vm,env,args=['--nocapture','--test-threads=1']);assert re.search(r'test result: ok\. 16 passed; 0 failed;',output.stdout.decode());record.update(label=label,profile=profile,passed=16);records.append(record);c.save('frozen-runtime-results.json',records)
 for profile in['debug','release']:
  a=json.loads((c.HERE/'artifacts'/('qualified-frozen-baseline-'+profile)/'test-list.json').read_text());b=json.loads((c.HERE/'artifacts'/('qualified-frozen-candidate-'+profile)/'test-list.json').read_text());assert a==b and len(a)==16
 print('64 fresh Frozen execution/parity integration tests passed in four isolated contexts')
if __name__=='__main__':main()
