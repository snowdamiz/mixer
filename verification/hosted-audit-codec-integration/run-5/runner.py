#!/usr/bin/env python3
"""Replay the isolated audit overlay against the accepted hosted application."""
import datetime, hashlib, io, json, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SHA=lambda b:hashlib.sha256(b).hexdigest()

def main():
    out=HERE/f'run-{int(sys.argv[1])}';out.mkdir(exist_ok=False)
    scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-audit-codec-'))
    project=scratch/'project';hosted=project/'hosted';hosted.mkdir(parents=True)
    commands=[];status='failed';inputs={};packages=[]
    env={**os.environ,'ERL_FLAGS':'+S 2:2','GIT_DIR':str(ROOT/'.git'),'GIT_WORK_TREE':str(ROOT)}
    def run(argv,cwd=hosted,timeout=300,check=True):
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            p=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
            code=p.returncode;log=p.stdout
        except subprocess.TimeoutExpired as e:code=124;log=(e.stdout or b'')+b'\nCOLLECTOR: timeout\n'
        path=out/f'command-{len(commands)+1:02}.log';path.write_bytes(log)
        commands.append({'argv':list(map(str,argv)),'cwd':str(cwd),'startedUTC':start,'exitCode':code,'log':path.name,'sha256':SHA(log)})
        if code and check:raise RuntimeError(f'command failed: {argv}; {path}')
        return log
    try:
        revision=run(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
        for path in subprocess.check_output(['git','ls-files','hosted'],cwd=ROOT).decode().splitlines():
            src=ROOT/path;target=project/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
            inputs[path]=SHA(src.read_bytes())
        for path in (HERE/'candidate').rglob('*'):
            if not path.is_file():continue
            target=hosted/path.relative_to(HERE/'candidate');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        for name in ['signed-release-v3.json','release-v3-cases.json']:
            p=ROOT/'services/protocol/testdata'/name;target=project/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        tested={str(p.relative_to(project)):SHA(p.read_bytes()) for p in sorted(project.rglob('*')) if p.is_file()}
        (out/'tested-source.json').write_text(json.dumps(tested,indent=2)+'\n')
        with tarfile.open(out/'source.tar.gz','w:gz') as archive:
            for path in tested:archive.add(project/path,arcname=path,recursive=False)
        lock=(hosted/'mix.lock').read_text()
        for line in lock.splitlines():
            m=re.match(r'  "([a-z_]+)": \{:hex, :\w+, "([^"]+)", "([a-f0-9]{64})"',line)
            if not m:continue
            name,version,inner=m.groups();outer=re.findall(r'"([a-f0-9]{64})"',line)[-1]
            data=(pathlib.Path.home()/'.hex/packages/hexpm'/f'{name}-{version}.tar').read_bytes()
            assert SHA(data)==outer
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                assert archive.extractfile('CHECKSUM').read().decode().strip().lower()==inner
                content=archive.extractfile('contents.tar.gz').read()
            files={}
            with tarfile.open(fileobj=io.BytesIO(content),mode='r:gz') as archive:
                for member in archive.getmembers():
                    if member.isdir():continue
                    path=pathlib.PurePosixPath(member.name)
                    assert member.isfile() and not path.is_absolute() and '..' not in path.parts
                    body=archive.extractfile(member).read();target=hosted/'deps'/name/member.name
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body);target.chmod(member.mode&0o777)
                    files[member.name]=SHA(body)
            packages.append({'name':name,'version':version,'archiveSHA256':outer,'innerChecksum':inner,'files':files})
        assert len(packages)==21
        (out/'dependencies.json').write_text(json.dumps(packages,indent=2)+'\n')
        run(['python3','--version']);run(['elixir','--version']);run(['mix','--version'])
        env['HEX_OFFLINE']='1'
        run(['mix','deps.get','--check-locked'])
        assert (hosted/'mix.lock').read_text()==lock
        for package in packages:
            for path,digest in package['files'].items():
                assert SHA((hosted/'deps'/package['name']/path).read_bytes())==digest
        env['MIX_ENV']='test'
        run(['mix','deps.compile'],timeout=300)
        run(['mix','compile','--warnings-as-errors'])
        run(['mix','test','test/mixer_hosted/audit/upload_event_test.exs','--warnings-as-errors','--seed','0','--trace'])
        # Full application, disposable PostgreSQL, and production release checks.
        run(['python3','scripts/test-local.py','--output',str(out/'full-hosted')],timeout=1200)
        assert all(SHA((ROOT/p).read_bytes())==v for p,v in inputs.items())
        status='passed'
    finally:
        shutil.rmtree(scratch)
        receipt={'status':status,'sourceRevision':locals().get('revision'),'commands':commands,
                 'baselineInputs':inputs,'testedSource':locals().get('tested'),
                 'sourceArchiveSHA256':SHA((out/'source.tar.gz').read_bytes()) if (out/'source.tar.gz').exists() else None,
                 'cleanup':{'ownedScratchRemoved':not scratch.exists()},
                 'environmentOverrides':{'ERL_FLAGS':'+S 2:2','GIT_DIR':'original checkout .git; revision observation only','GIT_WORK_TREE':'original checkout; no git mutations'},
                 'scope':'Isolated hosted pure audit component and full host regression/release checks; captured SQL rows only, no fresh domain SQL, migration, current-authority composition, HTTP, provider, native or GA acceptance.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'status':status,'receipt':str(out/'receipt.json'),'cleanup':receipt['cleanup']}))

if __name__=='__main__':main()
