#!/usr/bin/env python3
import json,re,shutil,sys
sys.dont_write_bytecode=True
import collect as c

def main():
    vm=c.source('adversarial');shutil.copytree(c.source('candidate'),vm)
    path=vm/'src/experimental_swift_reactor/memory_operations_tests.rs'
    path.write_bytes(path.read_bytes()+(c.HERE/'adversarial-memory-tests.rs').read_bytes())
    path=vm/'src/experimental_swift_reactor/control_tests.rs'
    path.write_bytes(path.read_bytes()+(c.HERE/'adversarial-control-tests.rs').read_bytes())
    before=c.manifest(c.source('candidate'));after=c.manifest(vm)
    assert sorted(n for n in before if before[n]!=after[n])==['src/experimental_swift_reactor/control_tests.rs','src/experimental_swift_reactor/memory_operations_tests.rs']
    c.archive('adversarial',vm)
    results=[]
    for profile in ['debug','release']:
        name='adversarial-all-'+profile;t=c.target(vm,'all',profile,'adversarial');env={'CARGO_TARGET_DIR':str(t)}
        p,_=c.command('build-'+name,['cargo','test','--lib','--no-run','--offline','--locked','--all-features',*(['--release']if profile=='release'else[]),'--message-format=json-render-diagnostics'],vm,env)
        rows=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')]
        a=[x for x in rows if x.get('reason')=='compiler-artifact'and x.get('executable')and x['profile']['test']and x['target']['name']=='mixer_vm'];assert len(a)==1 and a[0]['fresh']is False
        output,record=c.retain_and_run(name,a[0],vm,env,args=['review_r','--nocapture','--test-threads=1'])
        text=output.stdout.decode();assert 'test result: ok. 3 passed; 0 failed;'in text
        assert 'actualFunction=36 actualOffset='in text and 'nestedLegacyStage=Cleanup'in text
        record.update(profile=profile,selectedTests=[x for x in json.loads((c.HERE/'artifacts'/name/'test-list.json').read_text()) if'::review_r'in x],passed=3,reviewOnlyOverlay=True,productionBytesIdentical=True)
        results.append(record);c.save('adversarial-results.json',results)

if __name__=='__main__':main()
