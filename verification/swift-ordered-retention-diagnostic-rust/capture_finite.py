"""Finite evidence custody only, not the separately required target driver/analyzer."""
from pathlib import Path
import os,sys,json,stat,hashlib,io,datetime
P=Path(__file__).resolve().parent
MAX_STREAM=536871936;MAX_TWO=1073743872;SIDE=8192
KEYS=('dev','ino','mode','len','mtime_sec','mtime_nsec','ctime_sec','ctime_nsec')
def digest(data):return hashlib.sha256(data).hexdigest()
def metadata(s):return dict(zip(KEYS,[s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns//10**9,s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9]))
def regular(m):return stat.S_ISREG(m['mode'])
def stable(a,b):return a==b and regular(a)
def dump(path,value):
 raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode();assert len(raw)<=SIDE
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with io.FileIO(fd,'wb',closefd=True)as f:
  assert f.write(raw)==len(raw)
def capture(original,destination):
 initial=json.loads(original.with_suffix('.initial.json').read_text());final=json.loads(original.with_suffix('.final.json').read_text())
 rawresult=original.with_suffix('.original.txt').read_bytes();assert len(rawresult)<=8192
 # The Rust fixture persisted this authoritative original before footer creation.
 assert 'original_final_usage=' in rawresult.decode();result_sha=digest(rawresult)
 before=metadata(os.lstat(original));assert stable(final,before) and regular(initial) and initial['len']==0
 assert (initial['dev'],initial['ino'])==(final['dev'],final['ino'])
 assert 1024<=before['len']<=MAX_STREAM
 fd=os.open(original,os.O_RDONLY|os.O_NOFOLLOW);reader=io.FileIO(fd,'rb',closefd=True)
 source=metadata(os.fstat(fd));assert stable(source,before)
 copyfd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);copy=io.FileIO(copyfd,'wb',closefd=True)
 copy_initial=metadata(os.fstat(copyfd));assert copy_initial['len']==0 and regular(copy_initial)
 buffer=bytearray(65536);view=memoryview(buffer);whole=hashlib.sha256();copy_hash=hashlib.sha256();copied=0;blocks=0;maximum_attempts=0
 try:
  while copied<before['len']:
   blocks+=1;assert blocks<=8193;attempts=0
   while True:
    attempts+=1;assert attempts<=32
    try:n=reader.readinto(view[:min(65536,before['len']-copied)]);break
    except InterruptedError:pass
   assert n and n>0
   whole.update(view[:n]);offset=0
   while offset<n:
    attempts+=1;assert attempts<=32
    try:wrote=copy.write(view[offset:n])
    except InterruptedError:continue
    assert wrote and wrote>0;copy_hash.update(view[offset:offset+wrote]);offset+=wrote
   copied+=n;maximum_attempts=max(maximum_attempts,attempts)
  assert copied==before['len'];assert copied*2<=MAX_TWO
  after=metadata(os.fstat(fd));path_after=metadata(os.lstat(original));assert stable(source,after) and stable(after,path_after)
  copy_after=metadata(os.fstat(copyfd));assert stable(copy_after,metadata(os.lstat(destination)))
  assert (copy_after['dev'],copy_after['ino'])!=(source['dev'],source['ino'])
 finally:
  # FileIO exposes no fsync/durable-storage guarantee. A close exception fails
  # this finite operation; no second copy destination/retry is attempted.
  reader.close();copy.close()
 # Reverification replaces a closed copy descriptor, never a third live copy FD.
 verify_fd=os.open(destination,os.O_RDONLY|os.O_NOFOLLOW);verify=io.FileIO(verify_fd,'rb',closefd=True);sealed=hashlib.sha256();verified=0
 try:
  assert stable(copy_after,metadata(os.fstat(verify_fd)))
  while verified<copied:
   count=verify.readinto(view[:min(65536,copied-verified)]);assert count and count>0;sealed.update(view[:count]);verified+=count
  assert stable(copy_after,metadata(os.fstat(verify_fd))) and stable(copy_after,metadata(os.lstat(destination)))
 finally:verify.close()
 assert whole.digest()==copy_hash.digest()==sealed.digest()
 # Finite-frame-only status: no full replay or target result qualification.
 with io.FileIO(os.open(destination,os.O_RDONLY|os.O_NOFOLLOW),'rb',closefd=True)as framed:
  head=framed.read(512);framed.seek(-512,os.SEEK_END);footer=framed.read(512)
 words=[int.from_bytes(footer[i:i+8],'little')for i in range(0,512,8)]
 flags=words[9];status='invalid';failure=15
 # Full schema/replay acceptance is separate; this sidecar cannot claim complete.
 if flags==1:status='truncated-prefix';failure=0
 result={'version':1,'status':status,'selection_sha256':head[128:160].hex(),'schema_sha256':head[160:192].hex(),'header_sha256':digest(head),'original_result_sha256':result_sha,'stream_sha256':whole.hexdigest(),'stream_bytes':copied,'writer_initial':initial,'writer_final':final,'reader_before':source,'reader_after':after,'copy_before':copy_initial,'copy_after':copy_after,'copy_sha256':sealed.hexdigest(),'copy_bytes':copied,'copy_attempts':1,'metadata_results':[0]*8,'failure':failure}
 # Closed-frame fixture observation is separate from the conservative sidecar.
 observation={'ordinaryFlags':flags,'stored':words[2],'attempted':words[3],'fileBytes':copied,'blockCount':blocks,'maxCombinedAttempts':maximum_attempts,'originalPersistedBeforeSupplement':True,'fullReplayAccepted':False}
 assert (result['status']=='invalid' and result['failure']!=0)or(result['status']=='truncated-prefix' and result['failure']==0)
 dump(destination.with_suffix('.sidecar.json'),result)
 return observation

def inventory():
 # Conservative named Python host-copy value inventory, distinct from the Rust
 # live observer. Hash internals and FileIO/OS internals are not physical RSS.
 b=bytearray(65536);v=memoryview(b);s=os.stat(P);m=metadata(s)
 with io.FileIO(P/'writer.rs','rb')as measured_file:file_io_size=sys.getsizeof(measured_file)
 pieces={'oneCopyBuffer':sys.getsizeof(b),'threeMemoryviews':3*sys.getsizeof(v),'threeFileIOOwners':3*file_io_size,'eightStatResults':8*sys.getsizeof(s),'eightCustodyDictsDeep':8*(sys.getsizeof(m)+sum(sys.getsizeof(k)+sys.getsizeof(x)for k,x in m.items())),'threeHashOwners':3*sys.getsizeof(hashlib.sha256()),'twoRawResultCopiesCap':2*8192,'twoSidecarCopiesCap':2*8192,'sixteenCounters':16*sys.getsizeof(0),'fourPathOwners':4*512,'exceptionAndResultSlots':4096,'twoFrameBytesWithHeaders':2*sys.getsizeof(bytes(512))}
 return {'values':pieces,'total':sum(pieces.values()),'ceiling':131072,'scope':'finite Python host copy logical values; no physical stack/RSS claim'}
if __name__=='__main__':
 command=sys.argv[1];source=P/'.scratch/tmp-candidate'/command;destination=P/'streams'/command;destination.mkdir(parents=True,exist_ok=False)
 results={}
 for original in sorted(source.glob('ordered-*.bin')):
  if not all(original.with_suffix(s).exists()for s in ['.initial.json','.final.json','.original.txt']):continue
  results[original.name]=capture(original,destination/original.name)
 inv=inventory();assert inv['total']<=inv['ceiling']
 receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'finite custody, not full analyzer or target transport','observations':results,'hostCopyInventory':inv,'retainedStreamBytes':sum(p.stat().st_size for p in destination.glob('*.bin')),'python':sys.version,'executable':sys.executable}
 (P/(command+'-capture.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
