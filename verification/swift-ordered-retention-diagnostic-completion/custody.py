"""Bounded finite custody. No stream is semantically accepted by this helper.

Closed copy FileIO owners are confined to _copy and _inspect scopes. Descriptor
bound and named logical object inventory are separate from physical memory.
"""
from pathlib import Path
import datetime, hashlib, io, json, os, stat, struct, sys

P=Path(__file__).resolve().parent
MAX_STREAM=536871936
MAX_TWO=1073743872
SIDE=8192
KEYS=('dev','ino','mode','len','mtime_sec','mtime_nsec','ctime_sec','ctime_nsec')
SIDECAR_KEYS=('version','status','selection_sha256','schema_sha256','header_sha256',
    'original_result_sha256','stream_sha256','stream_bytes','writer_initial',
    'writer_final','reader_before','reader_after','copy_before','copy_after',
    'copy_sha256','copy_bytes','copy_attempts','metadata_results','failure')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def metadata(s):
    return dict(zip(KEYS,(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns//10**9,
        s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9)))
def regular(m): return stat.S_ISREG(m['mode'])
class Refusal(Exception):
    def __init__(self,code): self.code=code
def require(ok,code):
    if not ok: raise Refusal(code)
def stable(a,b): return a==b and regular(a)
def load_bounded(path,cap):
    with io.FileIO(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as file:
        before=metadata(os.fstat(file.fileno()));require(regular(before) and before['len']<=cap,'receipt-cap')
        # Enforce the allocation bound even if the owned receipt grows after its
        # first size observation. The one extra byte detects overflow safely.
        raw=file.read(cap+1);require(len(raw)<=cap,'receipt-cap')
        after=metadata(os.fstat(file.fileno()));require(stable(before,after) and stable(after,metadata(os.lstat(path))),'receipt-drift')
        require(len(raw)==before['len'],'receipt-short');return raw
def result_hash(path):
    raw=load_bounded(path,8192)
    require(b'original_final_usage=' in raw,'missing-original-result')
    return sha(raw)
def dump(path,value):
    # The text and encoded byte values coexist only in this final serialization
    # phase, after _copy and _inspect have returned all their FileIO owners.
    text=json.dumps(value,sort_keys=True,separators=(',',':'))+'\n'
    raw=text.encode();require(len(raw)<=SIDE,'sidecar-cap')
    with io.FileIO(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as out:
        require(out.write(raw)==len(raw),'sidecar-write')

class IO:
    """Finite source seam. Tests replace only operations on owned descriptors."""
    def readinto(self,source,view): return source.readinto(view)
    def write(self,destination,view): return destination.write(view)
    def observe(self,point,source,destination): pass
    def stat_path(self,path): return metadata(os.lstat(path))

def _copy(source_path,destination,expected,ops):
    source=None;copy=None;opened_destination=False
    try:
        # NONBLOCK avoids blocking on a fixture path changing to a FIFO before
        # the regular descriptor check. This is not a general race qualification.
        source=io.FileIO(os.open(source_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb')
        before=metadata(os.fstat(source.fileno()));require(stable(before,expected),'source-open-drift')
        copy=io.FileIO(os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
        opened_destination=True;initial=metadata(os.fstat(copy.fileno()))
        require(regular(initial) and initial['len']==0,'destination-initial')
        require((initial['dev'],initial['ino'])!=(before['dev'],before['ino']),'same-file')
        buffer=bytearray(65536);view=memoryview(buffer);original_hash=hashlib.sha256();copied_hash=hashlib.sha256()
        copied=0;blocks=0;maximum_attempts=0
        while copied<before['len']:
            blocks+=1;require(blocks<=8193,'block-cap');attempts=0
            while True:
                attempts+=1;require(attempts<=32,'attempt-cap')
                try: count=ops.readinto(source,view[:min(65536,before['len']-copied)]);break
                except InterruptedError: pass
            require(count is not None and 0<count<=min(65536,before['len']-copied),'source-short')
            original_hash.update(view[:count]);offset=0
            while offset<count:
                attempts+=1;require(attempts<=32,'attempt-cap')
                try: written=ops.write(copy,view[offset:count])
                except InterruptedError: continue
                require(written is not None and 0<written<=count-offset,'destination-short')
                copied_hash.update(view[offset:offset+written]);offset+=written
            copied+=count;maximum_attempts=max(maximum_attempts,attempts)
            ops.observe('block',source,copy)
        require(copied==before['len'] and copied*2<=MAX_TWO,'copy-cap')
        ops.observe('final',source,copy)
        after=metadata(os.fstat(source.fileno()));path_after=ops.stat_path(source_path)
        require(stable(before,after) and stable(after,path_after),'source-final-drift')
        final=metadata(os.fstat(copy.fileno()));destination_after=ops.stat_path(destination)
        require(stable(final,destination_after) and final['len']==copied,'destination-final-drift')
        require(original_hash.digest()==copied_hash.digest(),'copy-hash')
        return {'reader_before':before,'reader_after':after,'copy_before':initial,
            'copy_after':final,'copy_sha256':copied_hash.hexdigest(),'copy_bytes':copied,
            'stream_sha256':original_hash.hexdigest(),'stream_bytes':copied,
            'blockCount':blocks,'maxCombinedAttempts':maximum_attempts}
    finally:
        # Closing owners here does not retain them in caller scope. No fsync or
        # durable-close Result is inferred; a close exception refuses custody.
        try:
            if source is not None: source.close()
        finally:
            if copy is not None: copy.close()

def _inspect(destination,expected):
    # The previous two FileIO owners no longer exist. This function owns one
    # verification descriptor and reuses one copy buffer for full verification.
    with io.FileIO(os.open(destination,os.O_RDONLY|os.O_NOFOLLOW),'rb') as file:
        require(stable(expected,metadata(os.fstat(file.fileno()))),'verify-open-drift')
        buffer=bytearray(65536);view=memoryview(buffer);hashed=hashlib.sha256();read=0
        while read<expected['len']:
            count=file.readinto(view[:min(65536,expected['len']-read)])
            require(count is not None and count>0,'verify-short');hashed.update(view[:count]);read+=count
        require(stable(expected,metadata(os.fstat(file.fileno()))) and stable(expected,metadata(os.lstat(destination))),'verify-final-drift')
        file.seek(0);head=file.read(512);file.seek(max(0,expected['len']-512));footer=file.read(512)
        # These observations never determine sidecar acceptance, including CAP.
        observation={'ordinaryFlags':struct.unpack_from('<Q',footer,72)[0] if len(footer)==512 else None,
            'stored':struct.unpack_from('<Q',footer,16)[0] if len(footer)==512 else None,
            'attempted':struct.unpack_from('<Q',footer,24)[0] if len(footer)==512 else None,
            'headerBytes':len(head),'footerBytes':len(footer),'fullReplayAccepted':False}
        return hashed.hexdigest(),head,observation

def capture(original,destination,ops=None):
    ops=ops or IO()
    # Every rejection preserves any exclusive destination already created. The
    # outer failure receipt is separate from the closed sidecar schema.
    receipt={'copyAttempts':0,'status':'refused','error':None,'destinationRetained':False,'fullReplayAccepted':False}
    try:
        initial=json.loads(load_bounded(original.with_suffix('.initial.json'),2048))
        final=json.loads(load_bounded(original.with_suffix('.final.json'),2048))
        original_hash=result_hash(original.with_suffix('.original.txt'))
        before=ops.stat_path(original)
        require(regular(initial) and initial['len']==0 and stable(final,before),'writer-path-drift')
        require((initial['dev'],initial['ino'])==(final['dev'],final['ino']),'writer-identity')
        require(1024<=before['len']<=MAX_STREAM,'stream-cap')
        receipt['copyAttempts']=1
        copied=_copy(original,destination,before,ops)
        verified,head,observation=_inspect(destination,copied['copy_after'])
        require(verified==copied['copy_sha256'],'verify-hash')
        sidecar={'version':1,'status':'invalid','selection_sha256':head[128:160].hex(),
            'schema_sha256':head[160:192].hex(),'header_sha256':sha(head),
            'original_result_sha256':original_hash,
            **{k:copied[k] for k in ('stream_sha256','stream_bytes','reader_before','reader_after','copy_before','copy_after','copy_sha256','copy_bytes')},
            'writer_initial':initial,'writer_final':final,'copy_attempts':1,'metadata_results':[0]*8,'failure':15}
        require(set(sidecar)==set(SIDECAR_KEYS),'sidecar-schema')
        require(all(isinstance(sidecar[k],str) and len(sidecar[k])==64 for k in ('selection_sha256','schema_sha256','header_sha256','original_result_sha256','stream_sha256','copy_sha256')),'hash-shape')
        dump(destination.with_suffix('.sidecar.json'),sidecar)
        receipt.update(status='captured-invalid',observation=observation,copyBytes=copied['copy_bytes'],blockCount=copied['blockCount'],maxCombinedAttempts=copied['maxCombinedAttempts'])
    except Refusal as error: receipt['error']=error.code
    except (OSError,ValueError,KeyError,TypeError) as error: receipt['error']=type(error).__name__
    receipt['destinationRetained']=destination.exists()
    return receipt

def inventory():
    """Conservative named-object phase inventory, not physical Python/RSS.

    _copy and _inspect return before serialization. The explicit source scope
    eliminates closed FileIO owner accumulation. Dictionary deep values, stat
    tuples, heap buffers, views, hash owners, paths, exception/result locals,
    serialization copies, frame bytes, and interpreter-local reference slots
    are charged. CPython/json/hash/FileIO opaque internals remain unqualified.
    """
    sample=metadata(os.stat(P));deep_custody=sys.getsizeof(sample)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in sample.items())
    with io.FileIO(P/'custody.py','rb') as f: file_size=sys.getsizeof(f)
    common={'tenCustodyDictsDeep':10*deep_custody,'tenStatResultValues':10*sys.getsizeof(os.stat(P)),
        'sixPathsAndComponentStrings':6*1024,'resultAndObservationAndCopyDicts':8192,
        'hashDigestStringsAndBytes':12*128,'eightyScalarValues':80*32,
        'oneHundredLocalReferenceSlots':100*8,'exceptionAndResultOwners':4096}
    copy={**common,'oneCopyBuffer':sys.getsizeof(bytearray(65536)),'fourMemoryviewOwners':4*sys.getsizeof(memoryview(b'')),
        'twoFileIOOwners':2*file_size,'threeHashOwners':3*sys.getsizeof(hashlib.sha256()),'iteratorAndTemporarySliceOwners':2048}
    inspect={**common,'oneVerificationBuffer':sys.getsizeof(bytearray(65536)),'threeMemoryviews':3*sys.getsizeof(memoryview(b'')),
        'oneFileIOOwner':file_size,'oneHashOwner':sys.getsizeof(hashlib.sha256()),'twoFrameBytes':2*sys.getsizeof(bytes(512)),'iteratorAndTemporarySliceOwners':2048}
    serialize={**common,'twoBoundedMetadataRawCopies':2*2049,'oneOriginalResultRawCap':sys.getsizeof(bytes(8193)),
        'sidecarStringCap':sys.getsizeof('x'*8192),'sidecarBytesCap':sys.getsizeof(bytes(8192)),
        'oneSidecarFileIOOwner':file_size,'jsonEncoderListTupleAndKeyCopies':8192,'twoFrameBytes':2*sys.getsizeof(bytes(512))}
    phases={n:{'values':v,'total':sum(v.values())} for n,v in [('copy',copy),('verifyAndInspect',inspect),('serialize',serialize)]}
    peak=max(v['total'] for v in phases.values());require(peak<=131072,'host-logical-cap')
    return {'phases':phases,'peak':peak,'ceiling':131072,'scope':'named logical values; opaque physical/runtime memory unqualified'}

if __name__=='__main__':
    command=sys.argv[1];source=P/'.scratch/tmp-candidate'/command;destination=P/'streams'/command;destination.mkdir(parents=True,exist_ok=False)
    outcomes={}
    for original in sorted(source.glob('*.bin')):
        if all(original.with_suffix(s).exists() for s in ('.initial.json','.final.json','.original.txt')):
            outcomes[original.name]=capture(original,destination/original.name)
    receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outcomes':outcomes,'hostInventory':inventory(),
        'fullReplayAccepted':False,'python':sys.version,'executable':sys.executable,'scope':'finite custody only; closed sidecars invalid pending full replay'}
    (P/(command+'-capture.json')).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'captures':len(outcomes),'allCapturedInvalid':all(x['status']=='captured-invalid' for x in outcomes.values()),'hostLogicalPeak':receipt['hostInventory']['peak']}))
