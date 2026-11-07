import ast, hashlib, json, os, stat, sys
from pathlib import Path
ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/pair7-java-compile-ci-source-review/v3'
GUARD = ROOT / 'verification/rust-1991-actual-audit-preparation-v2/deny_runtime.py'
g = GUARD.read_bytes()
assert hashlib.sha256(g).hexdigest() == '69873787132f3c8d8f29977c87101e5c3d0337ae8429104bb49f1658b102cb74'
ns = {'__name__': 'review_old_guard', '__file__': str(GUARD)}
exec(compile(g, str(GUARD), 'exec'), ns)
ns['install'](OUT)
records = []
def read(rel, maximum=1048576):
    path = ROOT / rel
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode), rel
    assert before.st_size <= maximum, rel
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(fd)
        assert (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) == (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns), rel
        data = bytearray()
        while len(data) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not chunk: break
            data.extend(chunk)
        assert len(data) <= maximum, rel
        after = os.fstat(fd)
        assert (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) == (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns), rel
    finally: os.close(fd)
    records.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    return bytes(data)
if sys.argv[1] == 'show':
    for rel in sys.argv[2:]:
        data = read(rel)
        print(json.dumps(records[-1]))
        for i, line in enumerate(data.decode().splitlines(), 1): print(f'{i:4}: {line}')
elif sys.argv[1] == 'verify':
    packet = 'verification/pair7-java-compile-ci-proposal/v3/'
    seal = json.loads(read(packet+'seal.json'))
    assert records[-1]['sha256'] == '97eb9496823e087a5c8799985ac2f5157fd94b205574bcfb453d298def45145a'
    for m in seal['members']:
        data = read(packet+m['path'])
        assert len(data)==m['bytes'] and records[-1]['sha256']==m['sha256'], m
        if m['path'].endswith('.py'): ast.parse(data,filename=m['path'])
    read('.github/workflows/verify.yml')
    assert records[-1]['sha256']=='5ce51236f178080e3301289513fa3f5a8313e3a3969b0bab3f2b1cd4668de7f5'
    print(json.dumps({'packet_members':len(seal['members']),'packet_bytes':sum(m['bytes'] for m in seal['members']),'python_version':sys.version,'observations':records},indent=2))
else: raise ValueError('Unknown read action')
assert not ns['DENIED'], ns['DENIED']
log = OUT / ('reads-'+sys.argv[1]+'-'+hashlib.sha256(' '.join(sys.argv[2:]).encode()).hexdigest()[:12]+'.json')
with open(str(log), 'w') as handle: handle.write(json.dumps({'command':sys.argv,'python_version':sys.version,'old_guard_sha256':hashlib.sha256(g).hexdigest(),'denied_calls':ns['DENIED'],'reads':records},indent=2)+'\n')
