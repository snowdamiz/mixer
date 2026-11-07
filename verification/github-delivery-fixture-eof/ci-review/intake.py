#!/usr/bin/env python3
import sys
def deny(event,args):
 if event.startswith(('socket.','subprocess.')) or event in {'os.system','os.fork','os.posix_spawn','pty.spawn'}:raise RuntimeError('offline audit denied '+event)
sys.addaudithook(deny)
import datetime,hashlib,io,json,platform,signal,stat,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('40 second offline bound')));signal.alarm(40)
def digest(b):return hashlib.sha256(b).hexdigest()
results=[]
for role,size,sha in [('network',11899520,'117286f93e1df7773ff59bb6586688d810440b0f1a0726ddba9027b791758385'),('phoenix',825352,'e837cc5fdd331d18a518b58325f1d6f0f933ee8d3d11490aad033f02fb21781c')]:
 raw=(ROOT/(role+'-artifact.zip')).read_bytes();assert len(raw)==size and digest(raw)==sha
 seen=set();total=0;rows={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  for x in z.infolist():
   p=x.filename
   assert p and not p.startswith('/') and '\\' not in p and ':' not in p and chr(0) not in p and all(s not in ('','.','..') for s in p.split('/')) and str(PurePosixPath(p))==p
   assert p.casefold() not in seen and not x.is_dir() and not x.flag_bits&1 and stat.S_IFMT(x.external_attr>>16) in (0,stat.S_IFREG)
   total+=x.file_size;assert 0<=x.file_size<=256*1024*1024 and total<=256*1024*1024
   b=z.read(x);assert len(b)==x.file_size
   out=ROOT/role/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
   rows[p]={'bytes':len(b),'sha256':digest(b)};seen.add(p.casefold())
 result={'role':role,'zip_bytes':size,'zip_sha256':sha,'files':len(rows),'expanded_bytes':total,'members':rows};results.append(result)
 (ROOT/(role+'-intake-manifest.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='members'}))
 if role=='phoenix':
  for p in rows:
   if p.endswith(('format.log','receipt.json')) and ('phoenix-foundation' in p or p.endswith('format.log')):
    print(p);print((ROOT/role/p).read_text()[:15000])
receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':['/usr/bin/python3','-B',str(ROOT/'intake.py')],'python_version':platform.python_version(),'script_sha256':digest(Path(__file__).read_bytes()),'offline_audit_denies_network_and_children':True,'alarm_seconds':40,'scope':'ZIP integrity and bounded byte-only extraction of exactly selected GitHub network/Phoenix artifacts','product_code_executed':False,'results':[{k:v for k,v in r.items() if k!='members'} for r in results]}
(ROOT/'intake-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
