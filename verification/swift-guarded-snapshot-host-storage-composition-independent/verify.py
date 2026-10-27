"""Read-only frozen-packet replay; emits no files or product dispatch."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
from audit import HERE,ROOT,read,js,run_audit
def main():
    seal=js(HERE/'seal.json');members=seal['members']
    assert len(members)==seal['member_count']==len({x['path'] for x in members})
    for row in members:
        p=Path(row['path']);assert not p.is_absolute() and '..' not in p.parts
        data=read(HERE/p);assert (len(data),hashlib.sha256(data).hexdigest())==(row['bytes'],row['sha256']),p
    assert sum(x['bytes'] for x in members)==seal['member_bytes']
    assert run_audit()==js(HERE/'audit-results.json')
    p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','hostile_controls.py','-v'],cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,timeout=60,start_new_session=True)
    sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr)
    assert p.returncode==0 and b'Ran 20 tests' in p.stderr and b'\nOK\n' in p.stderr
    print(json.dumps({'own_frozen_members':len(members),'all_passed':True,'independent_methods':20,'conditional_storage_only':True,'native_or_GA':False},sort_keys=True))
if __name__=='__main__':main()
