#!/usr/bin/env python3
"""Independent old-engine replay, against full original baseline VM files."""
from pathlib import Path
import hashlib,io,json,os,re,subprocess,tarfile,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='39199ae5475de5d03926807ce60add5dcb0741c2';OLD=HERE/'legacy-tree';NEW=HERE/'tree'
def sha(b):return hashlib.sha256(b).hexdigest()
assert not OLD.exists();OLD.mkdir()
archive=subprocess.check_output(['git','archive',BASE,'vm'],cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(OLD,filter='data')
with tarfile.open(ROOT/'verification/swift-function-cache/frozen-source.tar.gz','r:gz') as tar:
    tests=tar.extractfile('vm/src/experimental/cache/tests.rs').read()
    decoder=tar.extractfile('vm/src/experimental/cache/decode.rs').read()
tests=tests[:tests.index(b'#[test]\nfn frozen_borrowed_transients_fit_existing_scratch')]
(OLD/'vm/src/experimental/cache/tests.rs').write_bytes(tests)
helper=decoder[decoder.index(b'#[cfg(test)]\npub(super) fn frozen_offsets'):]
with (OLD/'vm/src/experimental/cache/decode.rs').open('ab') as f:f.write(b'\n'+helper)
manifest={str(p.relative_to(OLD)):sha(p.read_bytes()) for p in sorted((OLD/'vm').rglob('*')) if p.is_file()}
(HERE/'legacy-input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],'TMPDIR':str(HERE/'tmp')}
pattern=re.compile(r'^(layout |offsets |scratch |new |miss |hit |release |invalid |cancel |allocation |precedence |eviction prefix )')
commands=[];comparisons=[]
for mode in ['debug','release']:
    for features in ['experimental-function-cache','experimental-swift-reactor,experimental-span-execution']:
        observations=[]
        for label,tree in [('original',OLD),('candidate1',NEW)]:
            env['CARGO_TARGET_DIR']=str(HERE/('build-legacy' if label=='original' else 'build'))
            argv=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features',features,'--lib']
            if mode=='release':argv+=['--release']
            argv+=['experimental::cache::tests::frozen_layout_and_trace_observation','--','--exact','--nocapture','--test-threads=1']
            start=time.monotonic();p=subprocess.run(argv,cwd=tree,env=env,capture_output=True,text=True);output=p.stdout+p.stderr
            log=f'legacy-{mode}-{"frozen" if features=="experimental-function-cache" else "swift-span"}-{label}.log';(HERE/log).write_text(output)
            assert p.returncode==0 and 'test result: ok. 1 passed; 0 failed;' in output,output
            lines=[line for line in p.stdout.splitlines() if pattern.match(line)]
            commands.append({'argv':argv,'cwd':str(tree),'target_dir':env['CARGO_TARGET_DIR'],'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':log,'output_sha256':sha(output.encode()),'exact_lines':len(lines)})
            observations.append(lines)
        assert observations[0]==observations[1]
        comparisons.append({'mode':mode,'features':features,'exact_lines':len(observations[0]),'equal':True,'observations_sha256':sha('\n'.join(observations[0]).encode())})
        (HERE/'independent-legacy.json').write_text(json.dumps({'baseline_revision':BASE,'baseline_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'commands':commands,'comparisons':comparisons,'scope':'same observation function added to unchanged old engine; no guest execution'},indent=2)+'\n')
        print(comparisons[-1],flush=True)
