import pathlib,json,hashlib,subprocess,tempfile,shutil,datetime
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer');p=root/'verification/swift-calls-dispatch-delivery-transport';out=root/'verification/swift-calls-dispatch-root-review/delivery-transport';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(p/'review-seal.json')=='f2215e914ab951535c693ef096b690bca3b9fee88e825c861f61b5a0af9d4619'
s=json.loads((p/'review-seal.json').read_text());print(s.keys())
for n,r in s['bindings'].items(): assert sha(p/n)==r['sha256'] and (p/n).stat().st_size==r['bytes'],n
manifest=json.loads((p/'transport-manifest.json').read_text());scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-v7-transport-')).resolve();inode=scratch.stat();result={}
try:
 for name in list(manifest['authority'])+manifest['excludedRawPaths']:(scratch/name).parent.mkdir(parents=True,exist_ok=True)
 for name in manifest['authority']:shutil.copyfile(root/name,scratch/name)
 argv=['python3','-B',str(p/'restore.py'),'--repo',str(scratch)];proc=subprocess.run(argv,cwd=root,capture_output=True,timeout=60)
 (out/'fresh-restore.stdout').write_bytes(proc.stdout);(out/'fresh-restore.stderr').write_bytes(proc.stderr);assert proc.returncode==0,proc.stderr
 result=json.loads(proc.stdout);assert all(x['result']=='created-verified-exact-raw-file' for x in result['restored'])
 for row in manifest['entries']:assert sha(scratch/row['path'])==row['sha256'] and (scratch/row['path']).stat().st_size==row['bytes']
 repeat=subprocess.run(argv,cwd=root,capture_output=True,timeout=60);assert repeat.returncode==0
 (out/'repeat-no-op.stdout').write_bytes(repeat.stdout);(out/'repeat-no-op.stderr').write_bytes(repeat.stderr)
 assert all(x['result']=='existing-byte-identical-no-op' for x in json.loads(repeat.stdout)['restored'])
 result={'schema':1,'sourceRevisionContext':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':argv,'exitCode':0,'transportSealSHA256':sha(p/'review-seal.json'),'restorerSHA256':sha(p/'restore.py'),'bindingsVerified':len(s['bindings']),'freshActualRawFilesRestored':2,'repeatExistingFilesUnmodified':2,'rawBytes':sum(x['bytes'] for x in manifest['entries']),'liveEvidenceChanged':False,'passed':True,'scope':'Actual fresh restoration into an owned temporary checkout skeleton; only authority files and two selected raw paths. No product execution or source edits.'}
finally:
 assert scratch.stat().st_dev==inode.st_dev and scratch.stat().st_ino==inode.st_ino
 shutil.rmtree(scratch);result['ownedScratchAbsent']=not scratch.exists()
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');(out/'review_transport.py').write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps(result,indent=2))
