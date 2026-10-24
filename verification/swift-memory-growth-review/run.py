#!/usr/bin/env python3
"""Independent review command collector; writes only this packet and owned scratch."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, subprocess, sys, tarfile, tempfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-memory-growth'
enc = lambda o: (json.dumps(o, sort_keys=True, indent=2) + '\n').encode()
sha = lambda b: hashlib.sha256(b).hexdigest()
def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(enc(obj))
def manifest(path):
    return {str(p.relative_to(path)): sha(p.read_bytes()) for p in sorted(path.rglob('*')) if p.is_file() and 'target' not in p.parts and '__pycache__' not in p.parts and p.name != '.DS_Store'}
def archive(path):
    with tarfile.open(path, 'r:gz') as t:
        members=t.getmembers()
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        out={m.name:t.extractfile(m).read() for m in members}
        assert len(out)==len(members)
        return out
def source_archive(tree, m, digest):
    dest=HERE/'sources'/(digest+'.tar.gz')
    if dest.exists(): return
    dest.parent.mkdir(exist_ok=True)
    with tarfile.open(dest, 'w:gz') as t:
        for p in m: t.add(tree/p, arcname=p, recursive=False)
def run(name, argv, cwd=None, env=None, source=None, binary=None):
    dest=HERE/'commands'/name
    assert not dest.exists(), name
    dest.mkdir(parents=True)
    m=manifest(source) if source else None
    digest=sha(enc(m)) if m is not None else None
    if source:
        write(dest/'source-manifest.json',m)
        source_archive(source,m,digest)
    e=os.environ.copy();e['PATH']='/opt/homebrew/opt/rustup/bin:'+e.get('PATH','');e.update(env or {})
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        p=subprocess.run(argv,cwd=cwd,env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except OSError as error:
        p=subprocess.CompletedProcess(argv,127,b'',str(error).encode())
    for stream,data in [('stdout',p.stdout),('stderr',p.stderr)]: (dest/(stream+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    after=manifest(source) if source else None
    row=dict(argv=list(map(str,argv)),cwd=str(cwd or ROOT),environment=dict(PATH=e['PATH'],**(env or {})),sourceTreeSHA256=digest,sourceBeforeSHA256=digest,sourceAfterSHA256=(sha(enc(after)) if after is not None else None),sourceUnchanged=(m==after),startedUTC=started,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,stdoutSHA256=sha(p.stdout),stderrSHA256=sha(p.stderr),executables=[])
    if binary:
        for path in binary:
            path=Path(path)
            row['executables'].append(dict(path=str(path),sha256=sha(path.read_bytes()),bytes=path.stat().st_size))
    write(dest/'receipt.json',row)
    print(name, 'exit',p.returncode, 'source',digest, flush=True)
    return p,row
def extract(data, dest):
    dest.mkdir(parents=True,exist_ok=True)
    for name,value in data.items():
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
def setup():
    HERE.mkdir(exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix='mixer-independent-growth-review-'))
    write(HERE/'scratch.json',dict(path=str(scratch),owned=True))
    baseline=archive(PRODUCER/'baseline-source.tar.gz');candidate=archive(PRODUCER/'candidate-source.tar.gz')
    extract(baseline,scratch/'baseline');extract(candidate,scratch/'candidate')
    changed={p for p in baseline.keys()|candidate.keys() if baseline.get(p)!=candidate.get(p)}
    import difflib
    diff=''.join(''.join(difflib.unified_diff(baseline.get(p,b'').decode().splitlines(True),candidate.get(p,b'').decode().splitlines(True),fromfile='baseline/'+p,tofile='candidate/'+p)) for p in sorted(changed))
    (HERE/'complete.diff').write_text(diff)
    write(HERE/'input-identities.json',dict(baselineFiles=len(baseline),candidateFiles=len(candidate),baselineSHA256=sha(enc({p:sha(v) for p,v in baseline.items()})),candidateSHA256=sha(enc({p:sha(v) for p,v in candidate.items()})),candidateArchiveSHA256=sha((PRODUCER/'candidate-source.tar.gz').read_bytes()),producerReceiptSHA256=sha((PRODUCER/'receipt.json').read_bytes()),producerSealSHA256=sha((PRODUCER/'seal.json').read_bytes()),changedPaths=sorted(changed)))
    run('rustc-version',['rustc','-vV'])
    run('cargo-version',['cargo','--version'])
    run('python-version',['python3','--version'])
    run('host-version',['uname','-a'])
    run('producer-offline-replay',['python3','-B',str(PRODUCER/'verify.py')])
    print(scratch)
if __name__=='__main__': setup()
