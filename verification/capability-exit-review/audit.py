#!/usr/bin/env python3
"""Audit committed source qualification and unchanged wire/dispatch contracts."""
import hashlib,json,pathlib,subprocess
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SOURCE=OUT/'.local/source'
REVISION=json.loads((OUT/'freeze.json').read_text())['revision']
EVIDENCE=SOURCE/'capabilities/verification/exit-observation'
receipt=json.loads((EVIDENCE/'receipt.json').read_text())
source=json.loads((EVIDENCE/'source-manifest.json').read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
assert source==receipt['source']
assert sha(json.dumps(source['files'],sort_keys=True,separators=(',',':')).encode())==source['digest']
for entry in source['files']:
    data=(SOURCE/entry['path']).read_bytes()
    assert len(data)==entry['bytes'] and sha(data)==entry['sha256'],entry['path']
assert len(source['files'])==49 and source['digest']=='24e6c520347a54fd31e74fdc6db185da6982f412e6068d078e9a64686da4dcc7'
assert sha((EVIDENCE/'verify.py').read_bytes())==receipt['evidenceRunnerSHA256']
commands=[]
for command in receipt['commands']:
    data=(SOURCE/command['output']).read_bytes()
    assert command['exitCode']==0 and sha(data)==command['outputSHA256'],command['name']
    commands.append({'name':command['name'],'command':command['command'],'exit_code':command['exitCode'],'output_sha256':command['outputSHA256'],'scope':command['scope']})
unchanged=['sdk/Sources/MixerCapabilities/GeneratedHostAdapters.swift','sdk/Sources/MixerCapabilities/GeneratedGuestAdapters.swift','sdk/Sources/MixerCapabilities/GeneratedModels.swift','capabilities/schema/v1.json','capabilities/java/mixer/capabilities/CapabilityCodec.java','capabilities/java/mixer/capabilities/CapabilityJSON.java','capabilities/java/mixer/capabilities/CapabilityModels.java','capabilities/plugins/network.http.v1.json','capabilities/plugins/storage.keyValue.v1.json']
for name in unchanged:
    assert (SOURCE/name).read_bytes()==subprocess.check_output(['git','show',REVISION+'^:'+name],cwd=ROOT),name
hashes=json.loads((SOURCE/'capabilities/schema/hashes.json').read_text())
prior=json.loads(subprocess.check_output(['git','show',REVISION+'^:capabilities/schema/hashes.json'],cwd=ROOT))
assert {k:v for k,v in hashes.items() if k!='nativeImplementationSHA256'}=={k:v for k,v in prior.items() if k!='nativeImplementationSHA256'}
assert hashes['nativeImplementationSHA256']!=prior['nativeImplementationSHA256']
p=subprocess.run(['python3','capabilities/tools/generate.py','--check'],cwd=SOURCE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OUT/'generated-check.log').write_bytes(p.stdout)
assert p.returncode==0,p.stdout
result={'revision':REVISION,'qualified_source_files':len(source['files']),'qualified_source_digest':source['digest'],'receipt_sha256':sha((EVIDENCE/'receipt.json').read_bytes()),'qualification_commands_audited':commands,'unchanged_wire_codec_dispatch_files':unchanged,'previous_native_identity':prior['nativeImplementationSHA256'],'current_native_identity':hashes['nativeImplementationSHA256'],'generator_check':{'command':['python3','capabilities/tools/generate.py','--check'],'cwd':str(SOURCE),'exit_code':p.returncode,'output':'generated-check.log','output_sha256':sha(p.stdout)},'environment':receipt['environment'],'scope':'Committed-source and command-log integrity audit; iOS/Android/WASI cross-builds and codec differential were audited rather than repeated. Cross-compilation is not device execution.'}
(OUT/'evidence-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('Matched49 immutable source files,',len(commands),'command logs, unchanged wire/dispatch bytes and regenerated native identity.')
