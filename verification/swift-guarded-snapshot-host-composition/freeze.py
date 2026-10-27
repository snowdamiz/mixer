"""Seal compact bounded evidence; no compiler, runtime or process inventory."""
import datetime
import json
import sys
sys.dont_write_bytecode=True
from prepare import HERE,sha,canonical,write
from verify import main as verify

def main():
    assert not (HERE/'seal.json').exists()
    verify()
    assert not (HERE/'owned-work').exists() and not (HERE/'owned-privacy-work').exists()
    assert not list(HERE.rglob('__pycache__'))
    members=[dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
       for p in sorted(HERE.rglob('*')) if p.is_file()]
    write('seal.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      member_count=len(members),members=members,manifest_sha256=sha(canonical(members)),
      scope='isolated exact146 source composition; metadata, pure synthetic interactions, privacy controls and invariant inventory only',
      genuine_runtime_full_quote_host_grant_native_OTA_GA_accepted=False))
    print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(members),bytes=sum(r['bytes'] for r in members))))

if __name__=='__main__':main()
