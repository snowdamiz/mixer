from runner import HERE,identity,run
from pathlib import Path
import subprocess,json,difflib,tarfile,shutil
ROOT=HERE.parents[2];REV='559858810e133640d52730972a6610e98442be6d'
binding=json.loads((HERE/'producer-inputs/source-binding.json').read_text())['files']
paths=sorted(binding);request=''.join(REV+':'+path+'\n' for path in paths).encode()
result=subprocess.run(['git','cat-file','--batch'],input=request,cwd=ROOT,capture_output=True,timeout=30,check=True)
(HERE/'accepted-git-batch-request.txt').write_bytes(request);(HERE/'accepted-git-batch-output.bin').write_bytes(result.stdout);(HERE/'accepted-git-batch.stderr').write_bytes(result.stderr)
cursor=0;differences={};equal=[]
for path in paths:
    end=result.stdout.index(b'\n',cursor);head=result.stdout[cursor:end].decode();cursor=end+1
    if head.endswith(' missing'):data=None
    else:
        blob,kind,size=head.split(' ');assert kind=='blob';length=int(size);data=result.stdout[cursor:cursor+length];cursor+=length+1
    current=(HERE/'candidate'/path).read_bytes()
    if data==current:equal.append(path);continue
    differences[path]={'accepted_git':identity(data) if data is not None else None,'candidate':identity(current)}
    dest=HERE/'diffs'/(path.replace('/','__')+'.diff');dest.parent.mkdir(exist_ok=True)
    dest.write_text(''.join(difflib.unified_diff((data or b'').decode().splitlines(keepends=True),current.decode().splitlines(keepends=True),fromfile=REV+':'+path,tofile='candidate:'+path)))
allowed=set(json.loads((HERE/'producer-inputs/owned-source-manifest.json').read_text()))
assert set(differences)==allowed,(set(differences)-allowed,allowed-set(differences))
parity=json.loads((HERE/'producer-inputs/native-input-parity.json').read_text())
archive=ROOT/parity['prior_archive'];data=archive.read_bytes();assert identity(data)==parity['archive_identity']
shutil.copyfile(archive,HERE/'accepted-native-source-archive.tar.gz')
consumer=HERE/'scratch/native-parity-consumer'
run('independent-native-input-parity-create',[HERE/'executables/cli-release/mixer','create','AppearanceConsumer','--application','dev.mixer.appearanceconsumer','--platform','android','--directory',consumer,'--sdk-path',HERE/'candidate/sdk','--android-adapter-path',HERE/'candidate/native/android'],timeout=180)
with tarfile.open(archive) as tar:
    for path,expected in parity['files'].items():
        member=tar.getmember('AppearanceConsumer/'+path);old=tar.extractfile(member).read();assert identity(old)==expected,path
        created=(consumer/path).read_bytes();assert created==old,path
report={'schema':1,'command':['git','cat-file','--batch'],'source_revision':REV,'batch_output':identity(result.stdout),'source_files':len(binding),'unchanged_source_files':len(equal),'changed_or_added_files':differences,'all_changes_within_root_selected_ownership':True,'accepted_native_archive':identity(data),'unchanged_native_target_input_files':len(parity['files']),'native_scope':parity['scope'],'ui_spec':identity((HERE/'candidate/contracts/ui-v1.json').read_bytes())}
(HERE/'independent-source-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='changed_or_added_files'},indent=2))
