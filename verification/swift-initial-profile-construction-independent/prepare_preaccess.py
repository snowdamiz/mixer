#!/usr/bin/env python3
"""Prepare only frozen pre-candidate inputs; never opens the implementation lane."""
from pathlib import Path
import datetime, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PROTOCOL = ROOT / 'verification/swift-initial-profile-construction-protocol'
CONTRACT = ROOT / 'verification/swift-initial-profile-protocol-independent'
ROW = ROOT / 'verification/swift-cache-state-profile-adapter'
ORIGINAL = ROOT / 'verification/swift-profile-header-preparation/inputs/vm'
OLD_ROW = ROOT / 'verification/swift-profile-header-preparation/inputs/verification/swift-cache-state-profile-adapter/source/vm'

def sha(b): return hashlib.sha256(b).hexdigest()
def emit(name, value):
    p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def member(p, name):
    b=p.read_bytes();return {'path':str(name),'bytes':len(b),'sha256':sha(b)}
def seal(base, expected):
    b=(base/'seal.json').read_bytes();assert sha(b)==expected
    d=json.loads(b)
    for m in d['members']: assert member(base/m['path'],m['path'])==m, m['path']
    assert len(d['members'])==d['member_count']
    assert sum(m['bytes'] for m in d['members'])==d['total_bytes']
    return {'path':str(base.relative_to(ROOT)),'seal_sha256':sha(b),'members':d['member_count'],'bytes':d['total_bytes']}

def leb(n):
    b=bytearray()
    while True:
        v=n&127;n>>=7;b.append(v|(128 if n else 0))
        if not n:return bytes(b)
def text(s):
    b=s.encode();return leb(len(b))+b
def fixture(count):
    # Hand-authored WebAssembly binary sections using the frozen official WASI
    # signature roster. No compiler or candidate source creates expected bytes.
    # Exact official descriptor source is independently converted below by a
    # literal reviewed roster, not parsed from the candidate implementation.
    imports=[
      ('args_get','ii'),('args_sizes_get','ii'),('environ_get','ii'),('environ_sizes_get','ii'),
      ('clock_res_get','ii'),('clock_time_get','iIi'),
      ('fd_close','i'),('fd_fdstat_get','ii'),('fd_fdstat_set_flags','ii'),
      ('fd_filestat_get','ii'),('fd_filestat_set_size','iI'),
      ('fd_filestat_set_times','iIIi'),('fd_pread','iiiIi'),('fd_prestat_get','ii'),
      ('fd_prestat_dir_name','iii'),('fd_read','iiii'),
      ('fd_readdir','iiiIi'),('fd_seek','iIii'),('fd_sync','i'),('fd_tell','ii'),
      ('fd_write','iiii'),('path_create_directory','iii'),('path_filestat_get','iiiii'),
      ('path_filestat_set_times','iiiiIIi'),('path_link','iiiiiii'),
      ('path_open','iiiiiIIii'),('path_readlink','iiiiii'),('path_remove_directory','iii'),
      ('path_rename','iiiiii'),('path_symlink','iiiii'),('path_unlink_file','iii'),('poll_oneoff','iiii'),
      ('proc_exit','i'),('random_get','ii')]
    # Validation of this literal roster is part of the real-validator old-source
    # probe. It is retained even if it is wrong; failures must never be hidden.
    sigs=[]
    for name,params in imports:
        returns=b'' if name=='proc_exit' else bytes([0x7f])
        p=bytes(0x7f if c=='i' else 0x7e for c in params)
        sigs.append(b'\x60'+leb(len(p))+p+leb(len(returns))+returns)
    sigs += [b'\x60\x00\x00',b'\x60\x00\x01\x7f',b'\x60\x00\x00']
    m=bytearray(b'\0asm\x01\0\0\0')
    def section(tag,b):
        start=len(m)+1+len(leb(len(b)));m.extend(bytes([tag])+leb(len(b))+b);return start
    section(1,leb(37)+b''.join(sigs))
    section(2,leb(34)+b''.join(text('wasi_snapshot_preview1')+text(name)+b'\0'+leb(i) for i,(name,_) in enumerate(imports)))
    types=[36 if i==0 else 35 if i==28 else 34 for i in range(count)]
    section(3,leb(count)+b''.join(leb(t) for t in types))
    section(4,b'\x01\x70\x01'+leb(46713)+leb(46713))
    section(5,b'\x01\x00'+leb(584))
    section(6,b'\x01\x7f\x01\x41\x00\x0b')
    section(7,b'\x03'+text('memory')+b'\x02\x00'+text('_initialize')+b'\x00'+leb(35)+text('mixer_fieldlog_corpus_v1')+b'\x00'+leb(62))
    code=bytearray(leb(count));relative=[]
    for i in range(count):
        body=b'\x00\x41\x00\x0b' if i==28 else b'\x00\x0b'
        code.extend(leb(len(body)));relative.append((len(code),len(body),types[i]));code.extend(body)
    start=section(10,bytes(code))
    rows=[(34+i,t,start+offset,n) for i,(offset,n,t) in enumerate(relative)]
    return bytes(m),rows

def main():
    custody={'schema':1,'scope':'PREACCESS, no candidate read or candidate acceptance','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    custody['seals']=[seal(PROTOCOL,'eee07facb219eaba5e135f3970d2f508a0acd20b3eb81f47f0dd9771412d5e91'),seal(CONTRACT,'9b1432883abeb5547d75ba59078e434b6105608adb5fc71590c00659e5852035'),seal(ROW,'472dc4fcffbca9718c9b7c47ced3586170ffd9ab1dbf7185b07e3b4cd2ff87a3')]
    selection=ROOT/'verification/swift-semantic-adapter-root-review/initial-profile-implementation-selection.json'
    assert sha(selection.read_bytes())=='be4b74efe70d5d009658eb6207f20457dbbe31537dab86a869d3cb5f17ede864'
    copies=[(selection,'inputs/initial-profile-implementation-selection.json')]
    copies += [(PROTOCOL/n,'inputs/'+n) for n in ['contract.md','protocol-types.rs','test-plan.md','local-structure-proposal.json','local-layout-type-index.json','test-budget-records.json','base-source-manifest.json','inputs/root/selected-host-budget.json','inputs/root/profile-header-selected-amendments.md','inputs/preparation/contract.json']]
    copies += [(CONTRACT/'future-closure.json','inputs/future-closure.json'),(ROOT/'verification/swift-semantic-adapter-root-review/profile-adapter-acceptance.json','inputs/profile-adapter-acceptance.json')]
    custody['copied_inputs']=[]
    for p,n in copies:
        q=OUT/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());custody['copied_inputs'].append(member(q,n))
    baseline=json.loads((PROTOCOL/'base-source-manifest.json').read_text())
    dest=OUT/'old-source/vm';assert not dest.exists(),'Never replace an existing source tree'
    baseline_locations=[]
    for m in baseline['members']:
        candidates=[r/m['path'] for r in [ORIGINAL,OLD_ROW,PROTOCOL/'source/vm']]
        p=next(p for p in candidates if p.is_file() and member(p,m['path'])==m)
        q=dest/m['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());baseline_locations.append({'path':m['path'],'copied_from':str(p.relative_to(ROOT))})
    assert len(baseline_locations)==134
    custody['baseline_locations']=baseline_locations
    emit('input-custody.json',custody)
    layout=json.loads((PROTOCOL/'local-structure-proposal.json').read_text())
    sizes={r['type']:r['bytes'] for r in layout['type_layout']}
    assert layout['derived_fields']['cache_header_bytes']==92128
    expected=[]
    for count in [29,67]:
        import struct
        b,rows=fixture(count)
        name=f'reactor-{count}'
        p=OUT/f'fixtures/{name}.wasm';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        sentinel=struct.pack('<IIQQQ',0,2**32-1,2**64-1,0,0)
        wire=bytearray(sentinel*80000)
        for absolute,t,offset,n in rows: wire[absolute*32:(absolute+1)*32]=struct.pack('<IIQQQ',1,t,offset,n,0)
        (OUT/f'fixtures/{name}.rows.bin').write_bytes(wire)
        slots=min(64,count);pins=64
        B=92128+slots*sizes['SwiftSlot']+pins*sizes['PinRecord']+512*sizes['decode::Patch']
        claims=bytes(range(256))
        header=bytearray(512);header[:8]=b'MIXPRF01'
        words=[1,512,32,80000,len(b),37,slots,pins,1,B,16777216,8388608,0,0,0]
        for i,w in enumerate(words,1): header[i*8:i*8+8]=struct.pack('<Q',w)
        header[128:384]=claims
        (OUT/f'fixtures/{name}.header.bin').write_bytes(header)
        expected.append({'id':name,'fixture_bytes':len(b),'defined':count,'imports':34,'types':37,'slots':slots,'pins':pins,'B':B,'wasm_sha256':sha(b),'header_sha256':sha(header),'row_body_sha256':sha(wire),'row_body_bytes':len(wire),'row_attempts_if_one_full_File_write_per_block':625,'descriptor_rows':[{'absolute':a,'type':t,'offset':o,'length':n} for a,t,o,n in rows]})
    emit('fixtures/expected.json',{'schema':1,'scope':'Independent exact expected bytes, not candidate execution or opaque-claim verification','opaque_claims':list(range(256)),'expectations':expected,'fixed_sizes_used':{n:sizes[n] for n in ['SwiftSlot','PinRecord','decode::Patch']}})
    emit('fixtures/slot-pin-grid.json',{'schema':1,'scope':'All 4096 selected grammar pairs, no runtime execution','pairs':[{'slots':s,'pins':p,'B':92128+s*sizes['SwiftSlot']+p*sizes['PinRecord']+512*sizes['decode::Patch']} for s in range(1,65) for p in range(1,65)]})
    print('PREACCESS verified 210+19+481 sealed members; copied exact baseline134; authored finite 29/67-definition fixtures and exact 512/2560000-byte expectations. No candidate was read.')

if __name__=='__main__':main()
