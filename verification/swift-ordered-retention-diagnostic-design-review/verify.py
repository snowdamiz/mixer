"""Read-only seal/closure verification with the two finite frozen model suites."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    h=hashlib.sha256(); size=0
    with path.open('rb') as stream:
        while block := stream.read(65536):
            h.update(block); size += len(block)
    return dict(bytes=size,sha256=h.hexdigest())


def main():
    seal_path=HERE/'seal.json'
    seal=json.loads(seal_path.read_text())
    if (HERE/'seal.sha256').read_text()!=digest(seal_path)['sha256']+'  seal.json\n':
        raise ValueError('seal digest')
    actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file()
            and p not in {HERE/'seal.json', HERE/'seal.sha256'}
            and not any(part.startswith('root-') for part in p.relative_to(HERE).parts)}
    actual.add('docs/swift-ordered-retention-diagnostic-design-review.md')
    if actual!=set(seal['members']):
        raise ValueError('exact review inventory')
    for name,expected in seal['members'].items():
        path=ROOT/name
        if '..' in Path(name).parts or path.is_symlink() or digest(path)!=expected:
            raise ValueError('review member drift: '+name)
    manifest=ROOT/'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json'
    if digest(manifest)['sha256']!=seal['baselineNamedClosure']:
        raise ValueError('named baseline manifest')
    declared=json.loads(manifest.read_text())
    if len(declared)!=132:
        raise ValueError('named baseline cardinality')
    def check_closure():
        for name,expected in declared.items():
            path=ROOT/'vm'/name
            if '..' in Path(name).parts or path.is_symlink() or digest(path)['sha256']!=expected:
                raise ValueError('named VM source drift: '+name)
    check_closure()
    results=[]
    for directory,pattern in ((HERE/'inputs/producer','test_*_model.py'), (HERE,'test_independent.py')):
        argv=[sys.executable,'-B','-m','unittest','discover','-s',str(directory),'-p',pattern,'-v']
        result=subprocess.run(argv,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0'),
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
        if result.returncode or max(len(result.stdout),len(result.stderr))>65536:
            sys.stderr.buffer.write(result.stderr[:65536])
            raise ValueError('finite frozen review failure')
        results.append(dict(argv=argv,summary=result.stderr.decode().splitlines()[-3:],
                            stdoutSHA256=hashlib.sha256(result.stdout).hexdigest(),stderrSHA256=hashlib.sha256(result.stderr).hexdigest()))
    check_closure()
    print(json.dumps(dict(status='pass',members=len(actual),sealSHA256=digest(seal_path)['sha256'],
                          baselineFiles=132,finiteResults=results,scope=seal['scope']),sort_keys=True))


if __name__ == '__main__':
    main()
