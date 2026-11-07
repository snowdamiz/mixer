from pathlib import Path
import json,subprocess,time,hashlib,tarfile,datetime
D=Path(__file__).resolve().parent;asset=json.loads((D/'jdk17-official-asset.json').read_bytes())[0];package=asset['binary']['package'];T=D/'owned-tool-scratch';T.mkdir(exist_ok=True);archive=T/package['name'];argv=['curl','--fail','--location','--max-time','55','--output',str(archive),package['link']];start=time.monotonic()
with (D/'jdk17-download.stdout').open('wb') as o,(D/'jdk17-download.stderr').open('wb') as e:r=subprocess.run(argv,stdout=o,stderr=e,timeout=60,check=False)
receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'exit':r.returncode,'timeout_seconds':60,'reaped':True,'elapsed_seconds':time.monotonic()-start,'official_release':asset['release_name'],'package':package}
(D/'jdk17-download-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert r.returncode==0
b=archive.read_bytes();assert len(b)==package['size'] and hashlib.sha256(b).hexdigest()==package['checksum'];receipt['download_checksum_verified']=True
with tarfile.open(archive) as tar:tar.extractall(T,filter='data')
archive.unlink();roots=list(T.glob('*/Contents/Home/bin/javac'));assert len(roots)==1;receipt['jdk_home']=str(roots[0].parents[1]);receipt['archive_removed_after_verified_extraction']=True;(D/'jdk17-download-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['jdk_home'])
