#!/usr/bin/env python3
"""Conditional focused and regression runner; every failure stops the matrix."""
import argparse,gzip,json,os,re,subprocess,tempfile,traceback
from pathlib import Path
import runtime_support as s
import node_check

FROZEN=['span_control_extraction','span_numeric_extraction','span_execution','span_execution_allocations','span_execution_oracle','span_function_cache','span_function_cache_allocations']

def plan():
    rows=[]
    for family in ['focused','library']:
        for feature in ['swift','all']:
            for profile in ['debug','release']:
                rows.append({'id':family+'-'+feature+'-'+profile,'family':family,'feature':feature,'profile':profile,'target':'mixer_vm','filter':'swift_lifecycle_'if family=='focused'else None})
    for feature in ['default','span']:
        for profile in ['debug','release']:
            rows.append({'id':'library-'+feature+'-'+profile,'family':'library','feature':feature,'profile':profile,'target':'mixer_vm','filter':None})
    for target in FROZEN:
        for profile in ['debug','release']:
            rows.append({'id':'frozen-'+target+'-'+profile,'family':'frozen','feature':'span','profile':profile,'target':target,'filter':None})
    for feature in ['default','span']:
        for profile in ['debug','release']:
            rows.append({'id':'check-'+feature+'-'+profile,'family':'check','feature':feature,'profile':profile})
    return rows

def flags(row):
    result=[]
    if row['feature']=='swift':result=['--no-default-features','--features','experimental-swift-reactor']
    elif row['feature']=='all':result=['--no-default-features','--all-features']
    elif row['feature']=='span':result=['--no-default-features','--features','experimental-span-execution']
    if row['profile']=='release':result+=['--release']
    return result

def observations(raw,names):
    text=raw.decode(errors='replace')
    starts=list(re.finditer(r'^test (\S+) \.\.\. ',text,re.M))
    assert [m[1]for m in starts]==names, 'actual executed identity order/set differs from fresh list'
    rows=[]
    for i,m in enumerate(starts):
        segment=text[m.end():starts[i+1].start()if i+1<len(starts)else len(text)]
        status='passed'if re.search(r'(^|\n)ok(\n|$)',segment)else'failed'if re.search(r'(^|\n)FAILED(\n|$)',segment)else'ignored'if segment.startswith('ignored')else'unresolved'
        rows.append({'test':m[1],'status':status,'fullPlannedSLRowComplete':False})
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--representation-selection',type=Path);ap.add_argument('--selection-sha256');ap.add_argument('--plan',action='store_true');args=ap.parse_args()
    if args.plan:print(s.enc(plan()).decode());return
    assert args.representation_selection and args.selection_sha256
    assert s.digest(args.representation_selection)==args.selection_sha256
    selection=s.read(args.representation_selection)
    assert s.SOURCE in json.dumps(selection), 'root selection does not bind candidate'
    # Root's concrete finite selection must be supplied; no implicit old selection.
    assert selection['schema']=='mixer.swift-lifecycle-test-repair-runtime-selection.1'
    assert selection['finiteRepresentationAccepted']is True and selection['additionalAccountingCredit']==0
    assert selection['candidateClosure']==s.SOURCE and len(selection['selectedNext'])==3
    assert selection['preRuntimeSealSHA256']==s.digest(s.HERE/'seal.json')
    assert selection['preRuntimeFreezeSHA256']==s.digest(s.HERE/'pre-runtime-freeze.json')
    subprocess.run([sys.executable,'-B',str(s.HERE/'verify_pre_runtime.py')],check=True)
    assert not (s.HERE/'runtime-results.json').exists(), 'no unchanged failed runtime reruns'
    s.save(s.HERE/'finite-representation-selection.json',args.representation_selection.read_bytes())
    s.save(s.HERE/'runtime-plan.json',plan())
    scripts={}
    for name in [p.name for p in sorted(s.HERE.glob('*.py'))]:
        raw=(s.HERE/name).read_bytes();s.save(s.HERE/'runtime-executed-scripts'/name,raw);scripts[name]=s.sha(raw)
    s.save(s.HERE/'runtime-driver-bindings.json',scripts)
    inventories=s.read(s.ACCOUNTING/'test-inventories.json')
    results=[];s.save(s.HERE/'runtime-results.json',results)
    for item in plan():
        folder=s.HERE/'runtime-attempts'/item['id'];folder.mkdir(parents=True)
        scratch=Path(tempfile.mkdtemp(prefix='mixer-lifecycle-v3-runtime-'))
        env=dict(os.environ,PATH=s.EXPLICIT_PATH,CARGO_TARGET_DIR=str(scratch/'target'),CARGO_INCREMENTAL='0')
        for key in ['RUSTFLAGS','RUSTC_BOOTSTRAP','RUSTC','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']:env.pop(key,None)
        result={'id':item['id'],'sourceClosure':s.SOURCE,'passed':False,'rootRepresentationSelectionSHA256':args.selection_sha256};results.append(result);s.save(s.HERE/'runtime-results.json',results)
        def command(name,argv,exe=None):
            assert s.digest(args.representation_selection)==args.selection_sha256
            return s.command(folder,name,argv,env,exe)
        try:
            if item['family']=='check':
                row,out,err=command('check',['cargo','check','--lib','--locked','--offline',*flags(item)])
                result.update(exitCode=row['exitCode'],passed=row['exitCode']==0)
            else:
                targetflags=['--lib']if item['target']=='mixer_vm'else['--test',item['target']]
                row,out,err=command('build',['cargo','test',*targetflags,'--no-run','--locked','--offline',*flags(item),'--message-format=json-render-diagnostics'])
                assert row['exitCode']==0,'build failed'
                artifacts=[json.loads(line)for line in out.decode().splitlines()if line.startswith('{')]
                artifacts=[x for x in artifacts if x.get('reason')=='compiler-artifact'and x.get('executable')and x['target']['name']==item['target']]
                assert len(artifacts)==1 and artifacts[0]['profile']['test']and not artifacts[0]['fresh']
                artifact=artifacts[0];exe=Path(artifact['executable']);assert exe.is_relative_to(scratch/'target')
                s.save(folder/'cargo-artifact.json',artifact)
                prefix=[item['filter']]if item['filter']else[]
                if item['target']=='span_execution_oracle':node_check.verify(env,folder)
                row,out,err=command('list',[str(exe),*prefix,'--list'],exe)
                assert row['exitCode']==0
                names=[line[:-6]for line in out.decode().splitlines()if line.endswith(': test')]
                assert names and len(names)==len(set(names))
                if item['family']=='focused':assert names==next(x['lifecycleTests']for x in inventories if x['context']==item['feature']+'-'+item['profile'])and len(names)==23
                s.save(folder/'exact-tests.json',names)
                row,out,err=command('execute',[str(exe),*prefix,'--nocapture','--test-threads=1'],exe)
                actual=observations(out,names)
                s.save(folder/'observed-identities.json',actual)
                text=out.decode(errors='replace')
                result.update(exitCode=row['exitCode'],tests=len(names),identitiesPassed=sum(x['status']=='passed'for x in actual),executableSHA256=row['executableSHA256'],passed=row['exitCode']==0 and all(x['status']=='passed'for x in actual)and f'{len(names)} passed; 0 failed; 0 ignored;'in text)
            s.save(s.HERE/'runtime-results.json',results)
            print(json.dumps(result,sort_keys=True),flush=True)
            assert result['passed'],'actual failure; matrix stopped without unchanged rerun'
        except BaseException:
            result['failure']=traceback.format_exc();s.save(s.HERE/'runtime-results.json',results);raise
        finally:s.cleanup(scratch,folder)
    s.save(s.HERE/'runtime-complete.json',{'sourceClosure':s.SOURCE,'commands':len(results),'focusedContexts':4,'exactLifecycleTestsPerContext':23,'allPlannedRowsComplete':False,'rootAcceptancePending':True})

if __name__=='__main__':
    import sys
    main()
