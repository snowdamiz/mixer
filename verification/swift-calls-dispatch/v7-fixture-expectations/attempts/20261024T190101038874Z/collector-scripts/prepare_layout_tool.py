"""Official exact rustc-dev preparation, owned scratch only; no shared changes."""
from pathlib import Path
import subprocess,sys,tempfile,urllib.request,hashlib,json,tomllib,datetime,os,tarfile,shutil,traceback
import collect as c
HERE=c.HERE
attempt=HERE/'tool-preparation'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');attempt.mkdir(parents=True)
scratch=Path(tempfile.mkdtemp(prefix='mixer-calls-exact-layout-tool-')).resolve()
records=[]
def fetch(url,name):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=scratch/name;shaurl=url+'.sha256'
 expected=urllib.request.urlopen(shaurl,timeout=30).read();c.save(attempt/(name+'.official-sha256'),expected)
 digest=expected.decode().split()[0];assert len(digest)==64
 h=hashlib.sha256();size=0
 with urllib.request.urlopen(url,timeout=60)as response,p.open('wb')as out:
  assert int(response.headers.get('Content-Length','0'))<2_000_000_000
  while block:=response.read(4*1024*1024):
   size+=len(block);assert size<2_000_000_000;h.update(block);out.write(block)
 assert h.hexdigest()==digest,(name,digest,h.hexdigest())
 records.append({'url':url,'checksumURL':shaurl,'sha256':digest,'bytes':size,'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()});c.save(attempt/'downloads.json',records)
 return p
try:
 rustc='/opt/homebrew/opt/rustup/bin/rustc';version=subprocess.check_output([rustc,'--version','--verbose'],text=True);sysroot=Path(subprocess.check_output([rustc,'--print','sysroot'],text=True).strip());c.save(attempt/'existing-compiler-version.log',version.encode());release=next(line.split(': ',1)[1]for line in version.splitlines()if line.startswith('release: '));host=next(line.split(': ',1)[1]for line in version.splitlines()if line.startswith('host: '));commit=next(line.split(': ',1)[1]for line in version.splitlines()if line.startswith('commit-hash: '))
 manifest=fetch('https://static.rust-lang.org/dist/channel-rust-'+release+'.toml','official-manifest.toml');c.save(attempt/'official-manifest.toml',manifest.read_bytes());dist=tomllib.loads(manifest.read_text());assert commit[:9] in dist['pkg']['rustc']['version'],(commit,dist['pkg']['rustc']['version']);component=dist['pkg']['rustc-dev']['target'][host];assert component['available']is True
 c.save(attempt/'selected-official-component.json',{'release':release,'host':host,'commit':commit,'metadata':component})
 archive=fetch(component['xz_url'],'rustc-dev.tar.xz');assert c.sha(archive.read_bytes())==component['xz_hash']
 # Materialize a new directory. Existing bytes are read-only hard links; no
 # installer runs and no existing destination is ever overwritten.
 own=scratch/'sysroot';own.mkdir()
 for file in sorted(sysroot.rglob('*')):
  rel=file.relative_to(sysroot);dest=own/rel
  if file.is_dir():dest.mkdir(exist_ok=True)
  elif file.is_symlink():dest.symlink_to(file.resolve())
  elif file.is_file():os.link(file,dest)
 extracted=scratch/'component';extracted.mkdir()
 with tarfile.open(archive)as t:t.extractall(extracted,filter='data')
 roots=[p for p in extracted.iterdir()if p.is_dir()];assert len(roots)==1
 payload=roots[0]/'rustc-dev';assert payload.is_dir()
 added={}
 for file in sorted(payload.rglob('*')):
  if not file.is_file():continue
  rel=file.relative_to(payload);dest=own/rel;data=file.read_bytes()
  if dest.exists():assert dest.read_bytes()==data,rel
  else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);added[str(rel)]=c.sha(data)
 c.save(attempt/'added-component-files.json',added)
 source_identity={str(p.relative_to(sysroot)):c.sha(p.read_bytes())for p in sorted(sysroot.rglob('*'))if p.is_file()and(p.parent.name=='lib' or p.name=='rustc')}
 c.save(attempt/'original-sysroot-bindings.json',source_identity)
 session={'scratch':str(scratch),'sysroot':str(own),'preparation':str(attempt.relative_to(HERE)),'rustcVersion':version,'officialManifestSHA256':c.sha(manifest.read_bytes()),'componentSHA256':component['xz_hash'],'status':'prepared-official-exact-component-no-runtime-acceptance'}
 c.save(HERE/'layout-tool-session.json',session);c.save(attempt/'result.json',session);print(json.dumps(session,indent=2))
except BaseException as error:
 c.save(attempt/'failure.log',traceback.format_exc().encode());c.save(attempt/'failure.json',{'type':type(error).__name__,'message':str(error),'scratch':str(scratch),'downloads':records,'accountingAccepted':False})
 shutil.rmtree(scratch);c.save(attempt/'cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'nativeInstancesCreated':0,'sharedToolchainModified':False});raise
