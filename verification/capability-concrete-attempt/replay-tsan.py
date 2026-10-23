#!/usr/bin/env python3
"""Replay an already linked TSan test bundle without xcrun's loader-env boundary."""
import hashlib,json,os,re,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    base_path=HERE/'2026-10-23-candidate-4/receipt.json';base=json.loads(base_path.read_text());source=Path(base['export'])
    out=HERE/'2026-10-23-tsan-replay-1';out.mkdir(exist_ok=False)
    launch=next(c for c in base['commands'] if c['name']=='tsan-tests');bundle=Path(launch['command'][-1])
    target=source.parent/'tsan/products/libMixerCapabilityActivationConcrete.dylib';executable=bundle/'Contents/MacOS/MixerConcreteTests'
    pins={str(target):sha(target),str(executable):sha(executable)}
    for name,digest in base['source_files'].items():assert sha(source/name)==digest
    env=os.environ|launch['environment'];began=time.monotonic()
    resolved=subprocess.run(['xcrun','--find','xctest'],env=os.environ|{'DEVELOPER_DIR':env['DEVELOPER_DIR']},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
    (out/'xctest-path.log').write_bytes(resolved.stdout);xctest=resolved.stdout.decode().strip();assert Path(xctest).is_file()
    command=[xctest,str(bundle)];result=subprocess.run(command,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (out/'tests.log').write_bytes(result.stdout);counts=[int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures',result.stdout)]
    record=dict(status='passed' if result.returncode==0 and counts and counts[-1]==6 and b'WARNING: ThreadSanitizer' not in result.stdout else 'failed check preserved',
        base_receipt=dict(path=str(base_path.relative_to(ROOT)),sha256=sha(base_path)),base_source_manifest_sha256=base['source_manifest_sha256'],base_source_unchanged=all(sha(source/n)==d for n,d in base['source_files'].items()),
        command=command,cwd=str(source),environment=launch['environment'],exit_code=result.returncode,observed_test_counts=counts,seconds=time.monotonic()-began,
        log_sha256=sha(out/'tests.log'),xctest_resolution_command=['xcrun','--find','xctest'],xctest_path_log_sha256=sha(out/'xctest-path.log'),artifacts=pins,
        artifacts_unchanged=all(sha(Path(p))==d for p,d in pins.items()),driver_sha256=sha(Path(__file__)),scope='Exact retained TSan test bundle/module replay; no source/module/package/Rust rebuild. Native/system code remains uninstrumented.')
    (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],sha(out/'receipt.json'));raise SystemExit(0 if record['status']=='passed' else 1)
if __name__=='__main__':main()
