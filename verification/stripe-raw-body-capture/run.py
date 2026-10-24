"""Replay isolated capture tests; never boot the production application or edit hosted.
Cache dependency BEAMs are copied and pinned against installed source and lockfile.
The candidate itself is always compiled freshly into unique disposable targets.
"""
import hashlib, json, os, platform, shutil, signal, subprocess, sys, socket, tarfile, tempfile, time, uuid
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXPECTED = 'eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, x): p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def files(base): return sorted(p for p in base.rglob('*') if p.is_file())
def main():
    number = 1
    while (HERE/f'run-{number}').exists(): number += 1
    result = HERE/f'run-{number}'; result.mkdir()
    commands=[]; cleanup={}; failure=None
    scratch=Path(tempfile.mkdtemp(prefix='mixer-stripe-raw-capture-'))
    identity=(scratch.stat().st_dev,scratch.stat().st_ino); token=str(uuid.uuid4())
    (scratch/'holder.json').write_text(json.dumps({'token':token,'pid':os.getpid(),'device':identity[0],'inode':identity[1]}))
    def run(label, argv, env=None, timeout=90):
        started=time.monotonic(); proc=subprocess.Popen(argv,cwd=scratch,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        expired=False
        try: output,_=proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired=True
            if os.getpgid(proc.pid)==proc.pid: os.killpg(proc.pid,signal.SIGTERM)
            try: output,_=proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                if os.getpgid(proc.pid)==proc.pid: os.killpg(proc.pid,signal.SIGKILL)
                output,_=proc.communicate(timeout=3)
        (result/f'{label}.log').write_bytes(output)
        record={'command':argv,'environmentOverrides':{k:env[k] for k in ['CAPTURE_SOURCE_DIR','CAPTURE_RESULT_DIR','CAPTURE_PHASE'] if env and k in env},'resolvedExecutable':os.path.realpath(shutil.which(argv[0])),'executableSHA256':sha(Path(shutil.which(argv[0])).resolve()),'cwd':str(scratch),'pid':proc.pid,'processGroup':proc.pid,'exitCode':proc.returncode,'timedOut':expired,'elapsedSeconds':round(time.monotonic()-started,3),'output':f'{label}.log','outputSHA256':sha(result/f'{label}.log')}
        commands.append(record); write(result/'commands.json',commands)
        if proc.returncode or expired: raise RuntimeError(f'{label} failed; retained output')
        return output.decode(errors='replace')
    try:
        selection=json.loads((REPO/'verification/stripe-raw-body-root-review/selection.json').read_text())
        assert selection['profile']==1
        for name, expected in selection['bindings'].items(): assert sha(REPO/name)==expected,(name,'selected evidence changed')
        for name, expected in selection['beamInputs'].items(): assert sha(REPO/name)==expected,(name,'selected dependency BEAM changed')
        pins=json.loads((HERE/'pinned-dependency-identity.json').read_text())
        assert sha(REPO/'hosted/mix.lock')==pins['lockSHA256']
        for name, expected in pins['source'].items(): assert sha(REPO/'hosted/deps'/name)==expected,(name,'dependency source pin changed')
        for name, expected in pins['beams'].items(): assert sha(REPO/'hosted/_build/test/lib'/name)==expected,(name,'dependency cache pin changed')
        for name, expected in pins['toolchain'].items(): assert sha(Path(name))==expected['sha256'],(name,'toolchain binary changed')
        write(result/'selected-bindings.json',{'sourceRevision':selection['sourceRevision'],'bindings':selection['bindings'],'beamInputs':selection['beamInputs']})
        observed={n:sha(REPO/n) for n in selection['sourceInputs']}
        digest=hashlib.sha256(json.dumps(observed,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert len(observed)==69 and observed==selection['sourceInputs'] and digest==EXPECTED
        write(result/'accepted-hosted-inputs.json',{'sourceRevisionFromSelection':selection['sourceRevision'],'sourceInputs':observed,'sourceDigest':digest})
        # Retain exact producer/contracts/accepted source, not mutable references.
        source=scratch/'source'; source.mkdir()
        input_names=['AGENTS.md','mixer-product-plan.md','docs/stripe-raw-body-direction.md','docs/stripe-raw-body-contract.md','verification/stripe-raw-body-root-review/selection.json','verification/stripe-raw-body-contract/test-matrix.json']+list(observed)+list(selection['bindings'])+[str(p.relative_to(REPO)) for p in files(REPO/'verification/stripe-raw-body-root-review')]
        for name in sorted(set(input_names)):
            dest=source/'inputs'/name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REPO/name,dest)
        for name in ['candidate','tests']:
            shutil.copytree(HERE/name,source/name)
        shutil.copyfile(HERE/'run.py',source/'run.py')
        shutil.copyfile(HERE/'pinned-dependency-identity.json',source/'pinned-dependency-identity.json')
        write(result/'source-inputs.json',{str(p.relative_to(source)):sha(p) for p in files(source)})
        with tarfile.open(result/'candidate-source-closure.tar.gz','w:gz') as archive:
            for p in files(source): archive.add(p,arcname=str(p.relative_to(source)),recursive=False)
        dep_source={str(p.relative_to(REPO/'hosted/deps')):sha(p) for p in files(REPO/'hosted/deps') if '.git' not in p.parts and '_build' not in p.parts}
        write(result/'dependency-source-inputs.json',dep_source)
        with tarfile.open(result/'dependency-source-closure.tar.gz','w:gz') as archive:
            for name in dep_source: archive.add(REPO/'hosted/deps'/name,arcname=name,recursive=False)
        cache=scratch/'dependency-cache'; cache.mkdir()
        beams={}
        for app in sorted((REPO/'hosted/_build/test/lib').iterdir()):
            if app.name=='mixer_hosted' or not (app/'ebin').is_dir(): continue
            shutil.copytree(app/'ebin',cache/app.name/'ebin')
            for p in files(cache/app.name): beams[str(p.relative_to(cache))]=sha(p)
        write(result/'dependency-beam-inputs.json',{'reuse':'copied existing pinned dependency cache; not a fresh dependency build','inputs':beams,'lockSHA256':sha(REPO/'hosted/mix.lock')})
        run('elixir-version',['elixir','--version'])
        run('python-version',['python3','--version'])
        run('os-version',['uname','-a'])
        otp_root=run('otp-root',['elixir','-e','IO.puts(:code.root_dir())']).strip()
        binaries=[Path(sys.executable).resolve(),Path(shutil.which('elixir')).resolve(),Path(shutil.which('erl')).resolve()]+sorted(Path(otp_root).glob('erts-*/bin/beam.smp'))
        write(result/'toolchain-executables.json',{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in binaries})
        args=['elixir']
        for path in sorted(cache.glob('*/ebin')): args+=['-pa',str(path)]
        args += [str(source/'tests/boot.exs')]
        for phase in ['component','wire']:
            if not (source/f'tests/{phase}.exs').exists(): continue
            phase_result=result/phase; phase_result.mkdir()
            env=dict(os.environ,CAPTURE_SOURCE_DIR=str(source),CAPTURE_RESULT_DIR=str(phase_result),CAPTURE_PHASE=phase)
            run(phase,args,env,timeout=180)
    except BaseException as exc:
        failure={'type':type(exc).__name__,'message':str(exc)}
    finally:
        groups=set(c['processGroup'] for c in commands)
        processes=subprocess.run(['ps','-axo','pid=,pgid=,command='],capture_output=True,text=True,timeout=10)
        remaining=[]
        for line in processes.stdout.splitlines():
            parts=line.strip().split(None,2)
            if len(parts)>=2 and parts[1].isdigit() and int(parts[1]) in groups: remaining.append(line)
        write(result/'owned-process-groups.json',{'groups':sorted(groups),'remaining':remaining,'psExit':processes.returncode})
        port_checks=[]
        for path in result.glob('*/listener.json'):
            port=json.loads(path.read_text())['port']
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.2): refused=False
            except ConnectionRefusedError: refused=True
            except OSError: refused=False
            port_checks.append({'port':port,'connectionRefused':refused})
        write(result/'post-process-port-checks.json',port_checks)
        holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True,text=True,timeout=30)
        (result/'scratch-holders.log').write_text(holders.stdout+holders.stderr)
        now=scratch.stat(); holder=json.loads((scratch/'holder.json').read_text())
        match=(now.st_dev,now.st_ino)==identity and holder['token']==token and holder['pid']==os.getpid()
        cleanup={'scratch':str(scratch),'device':identity[0],'inode':identity[1],'holderToken':token,'holderPID':os.getpid(),'identityMatched':match,'lsofExit':holders.returncode,'openHolders':bool(holders.stdout.strip()),'childCommandsExited':all(c['exitCode'] is not None for c in commands),'ownedProcessGroupsEmpty':not remaining,'portChecks':port_checks,'lsofCommand':['lsof','-nP','+D',str(scratch)],'processInventoryCommand':['ps','-axo','pid=,pgid=,command=']}
        if match and not remaining and holders.returncode==1 and not holders.stdout.strip() and all(c['connectionRefused'] for c in port_checks): shutil.rmtree(scratch)
        cleanup['scratchRemoved']=not scratch.exists()
        if not cleanup['scratchRemoved']: failure=failure or {'type':'CleanupFailure','message':'owned scratch retained due to identity or holder check'}
        write(result/'receipt.json',{'schema':1,'observedUTC':datetime.now(timezone.utc).isoformat(),'host':platform.platform(),'profile':1,'sourceDigest':EXPECTED,'commands':commands,'failure':failure,'cleanup':cleanup,'publicAdmissionAccepted':False,'productionChanged':False,'nativeStarted':False,'freshCandidateCompilation':True,'freshDependencyCompilation':False})
        write(result/'seal.json',{str(p.relative_to(result)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files(result) if p.name!='seal.json'})
    print(json.dumps({'run':result.name,'failure':failure,'cleanup':cleanup},sort_keys=True))
    if failure: raise SystemExit(1)
if __name__=='__main__': main()
