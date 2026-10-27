#!/usr/bin/env python3
"""Fresh-only bounded recorder for this lane's pure Python review."""
import hashlib,json,os
from pathlib import Path
import shutil,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
assert len(sys.argv)==2 and sys.argv[1].startswith('offline-review-attempt')
OUT=HERE/'commands'/sys.argv[1]
OUT.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
runner=HERE/'review_independent.py'
shutil.copyfile(runner,OUT/'reviewer.py')
argv=[sys.executable,str(runner)]
env=dict(PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1')
started=time.monotonic()
with (OUT/'stdout').open('wb') as stdout,(OUT/'stderr').open('wb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
    timed_out=False
    try:child.wait(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out=True
        os.killpg(child.pid,signal.SIGKILL)
        child.wait(timeout=5)
try:os.killpg(child.pid,0); absent=False
except ProcessLookupError:absent=True
receipt=dict(schema=1,argv=argv,cwd=str(ROOT),environment=env,python_version=sys.version,runner_sha256=sha(OUT/'reviewer.py'),recorder_sha256=sha(Path(__file__)),source_revision='975b2e3ef25255a882e7476780caa2e844ce928d',candidate_tree_sha256='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',exit_code=child.returncode,elapsed_seconds=time.monotonic()-started,timed_out=timed_out,owned_pid=child.pid,owned_pgid=child.pid,child_reaped=child.poll() is not None,owned_group_absent=absent,stdout_sha256=sha(OUT/'stdout'),stderr_sha256=sha(OUT/'stderr'),scope='Pure Python source/MIR/phase oracle; no compiler, product or native runtime')
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print((OUT/'stdout').read_text())
print((OUT/'stderr').read_text())
print(json.dumps(receipt))
sys.exit(child.returncode)
