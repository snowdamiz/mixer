#!/usr/bin/env python3
"""Independent host wire/source cross-check, not a validator or release authority."""
from pathlib import Path
import hashlib,json,struct
P=Path(__file__).resolve().parent
results=[]
for mode in ['debug','optimized']:
    base=P/'artifacts'/mode;source=(base/'actual-module.wasm').read_bytes();body=(base/'actual-rows.bin').read_bytes();meta=json.loads((base/'actual-module.json').read_text())
    assert len(source)==meta['source_extent']==2926 and len(body)==2560000
    assert source[:8]==b'\x00asm\x01\x00\x00\x00'
    anchor=meta['first_offset'];defined=[]
    for absolute in range(80000):
        row=struct.unpack_from('<IIQQQ',body,absolute*32)
        if 34<=absolute<164:
            i=absolute-34;expected_type=35 if i==28 else 129
            expected_bytes=b'\0'+b'\x01'*130+b'\x0b' if i==0 else (b'\0\x41\0\x0b' if i==28 else b'\0\x0b')
            offset=anchor if i==0 else anchor+133+(i-1)*3+(2 if i>28 else 0)
            assert row==(1,expected_type,offset,len(expected_bytes),0)
            assert source[offset:offset+len(expected_bytes)]==expected_bytes
            # Original encoded body-size prefix belongs before, not in, a body.
            prefix=b'\x84\x01' if i==0 else bytes([len(expected_bytes)])
            assert source[offset-len(prefix):offset]==prefix
            defined.append({'absolute':absolute,'type_index':expected_type,'offset':offset,'bytes':len(expected_bytes),'source_body_sha256':hashlib.sha256(expected_bytes).hexdigest()})
        else:assert row==(0,(1<<32)-1,(1<<64)-1,0,0)
    assert meta['second_offset']==anchor+133
    assert defined[1]['offset']!=defined[2]['offset'] and defined[1]['source_body_sha256']==defined[2]['source_body_sha256']
    results.append({'mode':mode,'source_sha256':hashlib.sha256(source).hexdigest(),'body_sha256':hashlib.sha256(body).hexdigest(),'exact_rows':80000,'import_sentinels':34,'defined_rows_source_compared':defined,'tail_sentinels':80000-164,'offset_anchor':'Independent test encoder first-body coordinate; all subsequent coordinates rederived by this host formula and checked against original body-size prefixes and instruction bytes','not_a_second_validator':True})
assert results[0]['source_sha256']==results[1]['source_sha256'] and results[0]['body_sha256']==results[1]['body_sha256']
(P/'actual-source-row-comparison.json').write_text(json.dumps({'schema':1,'results':results,'fixture_consumer_owner_provenance_claimed':False},indent=2)+'\n');print('Both modes: all80000 rows checked; all130 defined source bodies and original size prefixes independently compared')
