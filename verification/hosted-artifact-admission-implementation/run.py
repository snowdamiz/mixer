#!/usr/bin/env python3
"""Replay a frozen accepted hosted tree plus exact new-module overlay, offline."""
import datetime,hashlib,io,json,os,pathlib,re,shutil,subprocess,tarfile,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
BASE='4586bb901b980e9beeca5f7bb826f8b62140a3b4'

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(p.read_bytes())
def main():
    # A run is append-only; preserve every attempt rather than replacing logs.
    runs=sorted(p.name for p in OUT.glob('run-*') if p.is_dir())
    number=1
    while (OUT/f'run-{number}').exists():number+=1
    output=OUT/f'run-{number}';output.mkdir()
    scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-artifact-admission-',dir='/private/tmp'))
    commands=[];deps=[];status='failed';cleanup={};inputs={}
    helper_inputs={str(p.relative_to(ROOT)):digest(p) for p in [OUT/'run.py',OUT/'collect.exs',OUT/'compare.go',ROOT/'docs/hosted-artifact-admission-contract.md',ROOT/'verification/hosted-artifact-admission-contract/freeze.json']}
    def run(label,argv,cwd,env=None,check=True):
        log=output/(label+'.log');start=time.monotonic()
        with log.open('wb') as stream:
            try:r=subprocess.run(argv,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300);code=r.returncode
            except subprocess.TimeoutExpired:stream.write(b'COLLECTOR: 300 second deadline exceeded\n');code=124
        commands.append(dict(label=label,argv=list(map(str,argv)),cwd=str(cwd),environment={k:env[k] for k in ['MIX_ENV','HEX_OFFLINE','GOPROXY','GOSUMDB','GOTOOLCHAIN'] if env and k in env},exitCode=code,elapsedSeconds=time.monotonic()-start,output=log.name,outputSHA256=digest(log)))
        if code and check:raise RuntimeError(f'{label} failed ({code}); see {log}')
        return code
    try:
        archive=subprocess.check_output(['git','archive',BASE],cwd=ROOT)
        tarfile.open(fileobj=io.BytesIO(archive)).extractall(scratch,filter='data')
        # Isolated refs permit the accepted original hosted collector to record
        # revision without reading or changing the active checkout's refs/index.
        subprocess.run(['git','init','-q',str(scratch)],check=True)
        objects=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-path','objects'],cwd=ROOT,text=True).strip()
        (scratch/'.git/objects/info/alternates').write_text(objects+'\n')
        subprocess.run(['git','-C',str(scratch),'update-ref','refs/heads/main',BASE],check=True)
        subprocess.run(['git','-C',str(scratch),'symbolic-ref','HEAD','refs/heads/main'],check=True)
        for p in sorted((OUT/'overlay').rglob('*')):
            if p.is_file():
                relative=p.relative_to(OUT/'overlay');target=scratch/relative
                assert not target.exists(),f'overlay must only add new files: {relative}'
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        lock=(scratch/'hosted/mix.lock').read_text()
        for line in lock.splitlines():
            m=re.match(r'  "([^"]+)": \{:hex, :[^,]+, "([^"]+)".*"([0-9a-f]{64})"\},',line)
            if not m:continue
            name,version,want=m.groups();p=pathlib.Path.home()/'.hex/packages/hexpm'/f'{name}-{version}.tar'
            assert digest(p)==want,(name,'cached archive hash mismatch')
            outer=tarfile.open(p);contents=outer.extractfile('contents.tar.gz').read();dest=scratch/'hosted/deps'/name;dest.mkdir(parents=True)
            tarfile.open(fileobj=io.BytesIO(contents),mode='r:gz').extractall(dest,filter='data')
            deps.append(dict(name=name,version=version,archiveSHA256=want,archive=str(p)))
        assert len(deps)==20
        # Bind exact source closure for hosted compilation/tests and Go verifier.
        paths=[]
        for base in ['hosted','services/protocol']:
            paths.extend(p for p in (scratch/base).rglob('*') if p.is_file() and not {'_build','deps','.git','__pycache__'}.intersection(p.relative_to(scratch).parts))
        paths.extend(scratch/p for p in ['services/go.mod','services/go.sum'])
        for p in sorted(paths):inputs[str(p.relative_to(scratch))]=digest(p)
        with tarfile.open(output/'source.tar.gz','w:gz') as tar:
            for name in inputs:tar.add(scratch/name,arcname=name,recursive=False)
        shutil.copyfile(OUT/'compare.go',scratch/'services/compare_admission.go')
        shutil.copyfile(OUT/'collect.exs',scratch/'collect_admission.exs')
        env=dict(os.environ,HEX_OFFLINE='1',MIX_ENV='test',ERL_CRASH_DUMP_SECONDS='0',ERL_CRASH_DUMP=str(scratch/'erl_crash.dump'))
        run('elixir-version',['elixir','--version'],scratch,env)
        run('go-version',['go','version'],scratch,env)
        run('offline-locked-dependencies',['mix','deps.get','--check-locked'],scratch/'hosted',env)
        run('focused-tests',['mix','test','test/mixer_hosted/protocol/artifact_admission_test.exs','--warnings-as-errors','--trace'],scratch/'hosted',env)
        goenv=dict(env,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local')
        run('go-owned-protocol-regression',['go','test','./protocol','-count=1'],scratch/'services',goenv)
        run('go-same-input-comparison',['go','run','./compare_admission.go','protocol/testdata/signed-release-v3.json','protocol/testdata/release-v3-cases.json',str(output/'go-results.json')],scratch/'services',goenv)
        run('elixir-same-input-comparison-observations',['mix','run','--no-start',str(scratch/'collect_admission.exs'),str(scratch/'services/protocol/testdata/signed-release-v3.json'),str(scratch/'services/protocol/testdata/release-v3-cases.json'),str(output)],scratch/'hosted',env)
        assert json.loads((output/'go-results.json').read_text())==json.loads((output/'elixir-results.json').read_text()),'cross-language result or byte hash mismatch'
        # Invoke the accepted hosted integration collector unchanged. It owns and
        # cleans one disposable PostgreSQL fixture and builds a production release.
        run('accepted-hosted-full-suite',['python3','scripts/test-local.py','--output',str(output/'hosted')],scratch/'hosted',env)
        assert all(digest(scratch/name)==h for name,h in inputs.items()),'source changed during execution'
        status='passed'
    finally:
        if (scratch/'erl_crash.dump').exists():
            # Never retain a VM dump that could contain ephemeral test keys.
            (scratch/'erl_crash.dump').unlink()
        shutil.rmtree(scratch)
        cleanup={'isolatedSourceRemoved':not scratch.exists(),'ephemeralTestKeysPersisted':False,'existingProcessesOrDevicesTouched':False}
        receipt={'schema':1,'status':status,'baseRevision':BASE,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceInputs':inputs,'collectorInputs':helper_inputs,'sourceTreeSHA256':sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()),'sourceArchiveSHA256':digest(output/'source.tar.gz') if (output/'source.tar.gz').exists() else None,'dependencies':deps,'commands':commands,'cleanup':cleanup,'caseCounts':{'manifest':154,'origin':39,'namespace':14,'fixture':1,'assignmentOutOfScope':36},'scope':'New v3 artifact parser/standard signature+current-policy admission; accepted hosted regression suite+production release compile. No HTTP upload, membership/storage, provider, release execution, physical-device or GA qualification.'}
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'status':status,'receipt':str(output/'receipt.json'),'cleanup':cleanup}))
if __name__=='__main__':main()
