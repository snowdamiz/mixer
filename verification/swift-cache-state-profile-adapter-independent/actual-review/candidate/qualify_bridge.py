#!/usr/bin/env python3
"""Independent LE wire encoder around real validated rows; synthetic config only."""
from pathlib import Path
import hashlib,json,struct,sys
from run_command import P,run
ABS=(1<<64)-1

def words(values):return b''.join(struct.pack('<Q',v) for v in values)
def put(b,n,v):struct.pack_into('<Q',b,n*8,v)
def record(kind,meta,function=35):
    # Independently specified fixed event vocabulary; amounts are synthetic.
    r=[0,kind,0,1,0,0,function,meta['second_offset'],2,129,ABS,ABS,0,0,0,0]
    if kind==1:r[7:10]=[ABS]*3
    elif kind==3:r[15]=function&511
    elif kind==4:r[14]=ABS;r[15]=function&511
    elif kind==5:r[13:16]=[3,0,10]
    elif kind in (9,10):r[13]=3
    elif kind==11:r[10:16]=[0,0,1,1,3,1]
    elif kind==12:r[3]=0;r[8]=ABS;r[10:16]=[0,0,1,3,0,0]
    elif kind==13:r[2]=5;r[3]=0;r[6:10]=[ABS]*4;r[13]=5
    elif kind==14:r[6:10]=[ABS]*4;r[13:16]=[10,3,2]
    return r

def encode(meta,body,events,cap=False):
    capn=len(events) if cap else 2048
    c=bytearray(8192);p=bytearray(512)+body
    for i,v in enumerate([int.from_bytes(b'MIXFIX01','little'),1,8192,1,capn,33,meta['source_extent'],130,1,1,1,0,10,10,0,0]):put(c,i,v)
    for i,v in enumerate([int.from_bytes(b'MIXPRF01','little'),1,512,32,80000,meta['source_extent'],130,1,1,1,0,10,10,0,0,0]):put(p,i,v)
    h=[0]*64;h[:10]=[int.from_bytes(b'MIXORDR1','little'),1,512,128,512,capn,80000,64,512,33]
    # Protocol magic is defined as exact bytes MIXORDR1 by the selected source.
    stream=bytearray(words(h));operation=0
    for i,r in enumerate(events):
        r[0]=i+1;r[4]=10*(i+1);r[5]=i+1
        if r[1]==1:operation=r[3]
        stream+=words(r)
    last=events[-1];f=[0]*64;f[:16]=[int.from_bytes(b'MIXOEND1','little'),1,len(events),len(events)+int(cap),int(cap),len(events),last[4],last[5],operation,int(cap),last[4],last[5],0,0,ABS,33];f[33]=5;f[34]=1;f[35]=capn
    stream+=words(f)
    return stream,p,c

def main(mode):
    roster=json.loads((P/'required-bridge.json').read_text());meta=json.loads((P/'artifacts'/mode/'actual-module.json').read_text());body=(P/'artifacts'/mode/'actual-rows.bin').read_bytes();assert len(body)==2560000
    results=[];scratch=P/'scratch'/('bridge-'+mode);scratch.mkdir(parents=True,exist_ok=True);reports=P/'artifacts'/mode/'bridge-reports';reports.mkdir(exist_ok=True)
    for name in roster['invocations']:
        kinds=[13] if name=='phase_closed' else [1,2,3,4,5,9,10,11,12,13]
        if name=='failure14_unavailable':kinds=[1,14,13]
        events=[record(k,meta) for k in kinds];cap=name=='cap_unknown_tail'
        stream,profile,context=encode(meta,body,events,cap)
        expected=('ClosedFixtureObserved','Observed')
        row=512+35*32
        if name=='row_type_mismatch':struct.pack_into('<I',profile,row+4,128)
        elif name=='row_offset_mismatch':struct.pack_into('<Q',profile,row+8,meta['second_offset']+1)
        elif name=='row_length_mismatch':struct.pack_into('<Q',profile,row+16,1)
        elif name=='row_defined_zero':profile[row:row+32]=struct.pack('<IIQQQ',0,(1<<32)-1,ABS,0,0)
        elif name=='row_defined_two':struct.pack_into('<I',profile,row,2)
        elif name=='import_sentinel_type':struct.pack_into('<I',profile,512+4,0)
        elif name=='tail_sentinel_offset':struct.pack_into('<Q',profile,512+79999*32+8,0)
        elif name=='row_reserved_nonzero':struct.pack_into('<Q',profile,row+24,1)
        elif name in ['record_import','record_tail','equal_body_other_offset']:
            # Change one body-bearing event after encoding; header/footer stay valid.
            n=512+128
            if name=='record_import':struct.pack_into('<Q',stream,n+48,0)
            elif name=='record_tail':struct.pack_into('<Q',stream,n+48,79999)
            else:struct.pack_into('<Q',stream,n+56,meta['second_offset']+3)
        elif name=='failure14_unavailable':expected=('ApplicabilityUnavailable','FailureApplicability')
        elif name=='cap_unknown_tail':expected=('CapCutUnknownTail','Observed')
        elif name=='late_footer_invalid':stream[-512]=0
        if name not in ['phase_closed','miss_build_publish_release','failure14_unavailable','cap_unknown_tail']:expected=('Unavailable','FramingInvalid')
        paths=[];hashes=[]
        for key,data in [('stream',stream),('profile',profile),('context',context)]:
            path=scratch/(name+'-'+key+'.bin');path.write_bytes(data);paths.append(path);hashes.append({'kind':key,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        output=reports/(name+'.bin');argv=[str(P/'scratch'/('bridge-'+mode+'.bin')),str(paths[0]),str(paths[1]),str(paths[2]),str(output),*expected,name]
        ok=run('bridge-'+mode+'-'+name,argv);results.append({'name':name,'expected':expected,'passed':ok,'inputs':hashes,'report_bytes':output.stat().st_size if output.exists() else None,'report_sha256':hashlib.sha256(output.read_bytes()).hexdigest() if output.exists() else None})
        if not ok:break
    receipt={'mode':mode,'scope':'Real small-module row provenance; synthetic MIXPRF01 header and MIXFIX01 configuration/binding','required':roster['invocations'],'results':results,'passed':len(results)==len(roster['invocations']) and all(r['passed'] for r in results)}
    (P/f'bridge-qualification-{mode}.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed']
if __name__=='__main__':main(sys.argv[1])
