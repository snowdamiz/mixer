#!/usr/bin/env python3
"""Run the public Go/Swift protocol vector on an explicitly selected Android device."""
from pathlib import Path
import argparse, base64, hashlib, json, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--adb',required=True,type=Path)
p.add_argument('--device',required=True)
p.add_argument('--binary',required=True,type=Path)
p.add_argument('--libcxx',required=True,type=Path)
p.add_argument('--revision',required=True)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args()
vector_path=ROOT/'services/protocol/testdata/signed-release-v1.json'
vector=json.loads(vector_path.read_text())
commands=[]

def run(args,expected=0):
    command=[str(a.adb),'-s',a.device]+[str(x) for x in args]
    result=subprocess.run(command,text=True,capture_output=True,timeout=60)
    commands.append({'command':command,'exitCode':result.returncode})
    if result.returncode!=expected:raise AssertionError((command,result.returncode,result.stdout,result.stderr))
    return result.stdout

binary_digest=hashlib.sha256(a.binary.read_bytes()).hexdigest()
remote='/data/local/tmp/mixer-verifier-'+binary_digest[:12]
with tempfile.TemporaryDirectory(prefix='mixer-android-vector-') as temp:
    folder=Path(temp)
    for name,key in [('manifest','signed_manifest'),('assignment','signed_assignment'),('host','host'),('roots','roots')]:
        (folder/(name+'.json')).write_text(json.dumps(vector[key]))
    (folder/'payload.bin').write_bytes(base64.b64decode(vector['payload']))
    run(['shell','mkdir','-p',remote])
    run(['push',a.binary,a.libcxx,*sorted(folder.iterdir()),remote+'/'])
    executable=remote+'/'+a.binary.name
    run(['shell','chmod','700',executable])
    installed=run(['shell','sha256sum',executable]).split()[0]
    if installed!=binary_digest:raise AssertionError('Installed verifier bytes differ')
    command=['shell','env','LD_LIBRARY_PATH='+remote,executable,'verify']
    for key,name in [('manifest','manifest.json'),('payload','payload.bin'),('host','host.json'),('roots','roots.json'),('assignment','assignment.json')]:
        command+=['--'+key,remote+'/'+name]
    command+=['--channel',vector['signed_assignment']['assignment']['channel'],'--installation',vector['installation'],
              '--last-sequence',str(vector['last_sequence']),'--now','1792627300']
    actual=json.loads(run(command))
    assert actual['artifactSHA256']==vector['artifact_sha256']
    assert actual['cohortBucket']==vector['cohort_bucket'] and actual['assignmentSequence']==7
    assert not actual['activated'] and not actual['executableProfileVerified'] and not actual['policyApproved']
    command[command.index('--last-sequence')+1]='7'
    replay=json.loads(run(command,expected=1))
    assert replay['status']=='error' and 'sequence' in replay['message'].lower()
    receipt={'schema':1,'status':'passed','sourceRevision':a.revision,'verifierSHA256':binary_digest,
             'fixtureSHA256':hashlib.sha256(vector_path.read_bytes()).hexdigest(),
             'scope':'physical Android native Swift signature/canonical/cohort/replay vector only; fixture payload is non-executable',
             'device':{key:run(['shell','getprop',key]).strip() for key in ['ro.product.model','ro.build.version.release','ro.build.fingerprint']},
             'verification':actual,'replay':replay,'commands':commands,
             'limitations':['No VM execution or activation','Fixture pinned host metadata has ios scope; this tests protocol parity, not Android runtime binding','No key rotation/mobile recovery/store qualification']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='commands'},indent=2))
