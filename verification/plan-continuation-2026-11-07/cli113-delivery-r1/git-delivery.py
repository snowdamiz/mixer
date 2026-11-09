#!/usr/bin/env python3
import hashlib, importlib.util, json, os, re, shutil, sys, time
from pathlib import Path
ROOT=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4')
BASE=ROOT/'verification/plan-continuation-2026-11-07'
HERE=BASE/'cli113-delivery-r1'
CUST=BASE/'native-custody-premise/cleanup_control.py'
def need(v,m):
    if not v: raise RuntimeError(m)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,indent=2)+'\n');os.replace(t,p)
def main():
    phase=sys.argv[1];need(phase in ('inspect','commit','push','ci'),'unknown phase')
    cfg=json.loads((HERE/'execution-config.json').read_text())
    need(sha(HERE/'manifest.json')==cfg['manifestSHA256'],'manifest drift')
    manifest=json.loads((HERE/'manifest.json').read_text())
    rows=manifest['files']
    paths=[x['path'] for x in rows]+['verification/plan-continuation-2026-11-07/cli113-delivery-r1/manifest.json']
    need(len(paths)==len(set(paths))==cfg['allowlistCount'],'shipping allowlist')
    for row in rows: need(sha(ROOT/row['path'])==row['sha256'],'shipping file drift '+row['path'])
    need(sha(CUST)=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df','custodian drift')
    git=Path(cfg['gitPath']);need(git.is_file() and os.access(git,os.X_OK),'git unavailable')
    need(sha(git)=='10f9c1df894525ae4c7454258febab6d3d25071062b42cb48dbb1842cdffd2a9','git identity drift')
    need(sha(Path(sys.executable))=='e401ac7a95cda75dee34a0cfe1e4faf0a6df1a501cf67887f177fb78cd4eb60a','python identity drift')
    out=HERE/('git-'+phase);need(out.is_dir() and not (out/'receipt.json').exists(),'fresh prepared phase required')
    intent=json.loads((out/'prelaunch.json').read_text());need(intent['helperSHA256']==sha(HERE/'git-delivery.py'),'helper drift')
    need(intent['manifestSHA256']==cfg['manifestSHA256'],'intent manifest')
    for r in intent['identities']:
        p=Path(r['path']);s=p.lstat();need(p.is_dir() and not p.is_symlink() and [s.st_dev,s.st_ino,s.st_uid]==r['identity'],'phase directory drift')
    scratch=out/'scratch'
    remaining=180-(time.time()-intent['epoch']);need(0<remaining<=180,'phase deadline expired')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),GIT_TERMINAL_PROMPT='0')
    spec=importlib.util.spec_from_file_location('delivery_custodian',CUST);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    started=time.monotonic();active=started+remaining;commands=mod.Commands(out,env,deadline=active+60,cleanup_seconds=60)
    receipt={'schema':1,'phase':phase,'status':'ADMITTED','source113':manifest['source113'],'manifestSHA256':cfg['manifestSHA256'],'allowlist':paths,'git':{'path':str(git),'sha256':sha(git)},'scratchIdentity':{'path':str(scratch),'device':scratch.stat().st_dev,'inode':scratch.stat().st_ino},'budgets':{'activeSeconds':180,'cleanupReserveSeconds':60,'commandSeconds':90,'commandBytes':8388608,'aggregateBytes':67108864},'primaryTransportCustody':'not independently certified'}
    save(out/'receipt.json',receipt)
    def run(label,args,allowed=(0,)):
        need(time.monotonic()<active-15 and len(commands.records)<12 and not commands.hold and not commands.limit,'insufficient active budget or closed admission')
        return commands.run(label,[str(git),'-c','gc.auto=0','-c','maintenance.auto=false',*args],ROOT,timeout=min(90,active-time.monotonic()),allowed=allowed)
    def head(): return run('head',['rev-parse','HEAD']).strip()
    def remote():
        text=run('remote-main',['ls-remote','--exit-code','origin','refs/heads/main'])
        values=re.findall(r'(?m)^([0-9a-f]{40})\s+refs/heads/main$',text)
        need(len(values)==1,'ambiguous remote main');return values[0]
    def staged(): return {p for p in run('staged-paths',['diff','--cached','--name-only','-z']).split('\0') if p}
    error=None
    try:
        receipt['gitVersion']=run('git-version',['--version']).strip()
        if phase=='inspect':
            receipt['head']=head();need(receipt['head']==manifest['baseHEAD'],'HEAD changed')
            receipt['branch']=run('branch',['symbolic-ref','--short','HEAD']).strip();need(receipt['branch']=='t3/84a22cd4','branch mismatch')
            before=staged();need(not before,'pre-existing staged files; left unchanged')
            receipt['preexistingStaged']=sorted(before)
            run('whitespace',['diff','--check','--',*paths])
            receipt['originURL']=run('origin-url',['remote','get-url','origin']).strip();need(receipt['originURL'] in ('https://github.com/snowdamiz/mixer.git','git@github.com:snowdamiz/mixer.git','https://github.com/snowdamiz/mixer'),'unexpected origin')
            receipt['remoteMain']=remote();need(receipt['remoteMain']==manifest['baseHEAD'],'remote main moved; no force or merge')
            receipt['status']='PREFLIGHT_PASSED'
        elif phase=='commit':
            pre=json.loads((HERE/'git-inspect/receipt.json').read_text());need(pre['status']=='PREFLIGHT_PASSED','preflight missing')
            need(head()==manifest['baseHEAD'],'HEAD changed')
            need(staged()<=set(paths),'unrelated staged files; left unchanged')
            run('stage-exact-allowlist',['add','-f','--',*paths])
            staged_paths=staged();need(staged_paths and staged_paths<=set(paths),'unexpected staged set')
            info=run('index-bindings',['ls-files','--stage','-z','--',*paths])
            actual={}
            for raw in info.split('\0'):
                if not raw: continue
                meta,name=raw.split('\t',1);mode,blob,stage=meta.split()
                need(stage=='0','unmerged index');actual[name]=(mode,blob)
            for row in rows: need(actual.get(row['path'])==(row['mode'],row['gitBlobSHA1']),'index blob/mode mismatch '+row['path'])
            mb=(HERE/'manifest.json').read_bytes();blob=hashlib.sha1(b'blob '+str(len(mb)).encode()+b'\0'+mb).hexdigest()
            need(actual.get(paths[-1])==('100644',blob),'manifest index mismatch')
            run('staged-whitespace',['diff','--cached','--check','--',*paths])
            receipt['stagedPaths']=sorted(staged_paths)
            receipt['commitOutput']=run('commit',['commit','--file',str(HERE/'commit-message.txt')])
            receipt['head']=head();receipt['parent']=run('parent',['rev-parse','HEAD^']).strip()
            need(receipt['parent']==manifest['baseHEAD'] and receipt['head']!=manifest['baseHEAD'],'unexpected commit ancestry')
            receipt['tree']=run('tree',['rev-parse','HEAD^{tree}']).strip();need(not staged(),'staged state remains')
            receipt['status']='COMMITTED_EXACT_ALLOWLIST'
        elif phase=='push':
            commit=json.loads((HERE/'git-commit/receipt.json').read_text());need(commit['status']=='COMMITTED_EXACT_ALLOWLIST','validated commit missing')
            need(head()==commit['head'],'HEAD drift before push')
            receipt['head']=commit['head'];before=remote();receipt['remoteBefore']=before
            need(before in (manifest['baseHEAD'],commit['head']),'remote main moved; no force or merge')
            if before!=commit['head']:
                receipt['pushOutput']=run('push-origin-main',['push','origin','HEAD:main'],allowed=(0,1,128))
                receipt['pushExit']=commands.records[-1]['exit_code']
            else: receipt['pushAlreadyObserved']=True
            receipt['remoteAfter']=remote();need(receipt['remoteAfter']==commit['head'],'push not confirmed; inspect without repeating')
            receipt['status']='PUSH_CONFIRMED'
        else:
            push=json.loads((HERE/'git-push/receipt.json').read_text());need(push['status']=='PUSH_CONFIRMED','confirmed push missing')
            gh=Path(cfg['ghPath']);need(gh.is_file() and os.access(gh,os.X_OK),'gh unavailable')
            argv=[str(gh),'api','repos/snowdamiz/mixer/actions/runs?head_sha='+push['head']+'&per_page=10']
            receipt['gh']={'path':str(gh),'sha256':sha(gh)}
            receipt['ciOutput']=commands.run('ci-runs',argv,ROOT,timeout=60)
            data=json.loads(receipt['ciOutput'])
            receipt['runs']=[{k:v.get(k) for k in ('id','name','path','event','status','conclusion','head_sha','html_url')} for v in data.get('workflow_runs',[])]
            need(all(r['head_sha']==push['head'] for r in receipt['runs']),'CI head mismatch')
            receipt['head']=push['head'];receipt['status']='CI_OBSERVED'
    except BaseException as exc:
        error=repr(exc);receipt['status']='FAILED';receipt['error']=error
    finally:
        terminal=bool(commands.records) and not commands.hold and all(x['terminal_custody'] for x in commands.records)
        for r,item in zip(commands.records,commands.owned):
            r['descriptors_closed']=all(getattr(item['process'],n).closed for n in ('stdout','stderr'))
        commands.flush()
        receipt.update(commands=commands.records,hold=commands.hold,limit=commands.limit,allManagedTerminalCustody=terminal,elapsedSeconds=time.monotonic()-started)
        if commands.hold or commands.limit or not terminal:
            receipt['status']='FAILED'
            if commands.hold:save(out/'HOLD.json',{'hold':commands.hold,'scratch':str(scratch),'commands':commands.records,'noFurtherProcessOperations':True})
        if not error and not commands.hold and not commands.limit and terminal:
            clean=commands.cleanup(scratch);receipt['cleanup']=clean;receipt['scratchRemoved']=clean['scratchRemoved']
        else: receipt['scratchRemoved']=False;receipt['failedScratchRetained']=True
        save(out/'receipt.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ['phase','status','head','remoteMain','remoteAfter','runs','allManagedTerminalCustody','scratchRemoved','hold','limit','error','elapsedSeconds']}),flush=True)
    return 0 if receipt['status']!='FAILED' else 1
if __name__=='__main__': sys.exit(main())
