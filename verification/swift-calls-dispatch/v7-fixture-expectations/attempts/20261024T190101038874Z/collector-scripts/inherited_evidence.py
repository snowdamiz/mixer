"""Explicit source/compiler-bound reuse of unchanged baseline and selected history."""
import collect as c
parent=c.HERE.parent
seal=c.read_json(parent/'review-seal.json');assert c.sha((parent/'review-seal.json').read_bytes())=='7d5a043e7c982a84d5fe1a85444a6a492a40ebddf87a36e95ebdedde02593b15'
records=[]
for cfg in c.read_json(parent/'final-query-bindings.json'):
 name=f'paired-layout-baseline-{cfg}.json';p=c.HERE/name;r=c.read_json(p)
 assert p.read_bytes()==(parent/name).read_bytes()and r['sourceClosure']==seal['baselineSourceClosure']
 a=c.HERE/r['attempt'];command=c.read_json(a/'command.json');tools=c.read_json(a/'tools.json');assert command['sourceUnchanged']and command['exitCode']==0 and tools['actualCompiler']['sysrootCompilerFilesSHA256']
 records.append({'kind':'unchanged-baseline-paired-layout','config':cfg,'path':name,'sha256':c.sha(p.read_bytes()),'attempt':r['attempt'],'sourceClosure':r['sourceClosure'],'commandSHA256':c.sha((a/'command.json').read_bytes()),'toolsSHA256':c.sha((a/'tools.json').read_bytes()),'actualCompiler':tools['actualCompiler'],'parentSealSHA256':c.sha((parent/'review-seal.json').read_bytes())})
f=c.read_json(parent/'frozen-identity.json')['baseline'];a=c.HERE/f['attempt'];command=c.read_json(a/'command.json');tools=c.read_json(a/'tools.json');assert command['sourceClosure']==seal['baselineSourceClosure']and command['exitCode']==0
records.append({'kind':'unchanged-baseline-expanded-methods','attempt':f['attempt'],'sourceClosure':command['sourceClosure'],'methods':f['methods'],'commandSHA256':c.sha((a/'command.json').read_bytes()),'toolsSHA256':c.sha((a/'tools.json').read_bytes()),'actualCompiler':tools['actualCompiler']})
c.save(c.HERE/'inherited-baseline-evidence.json',{'parentSealSHA256':c.sha((parent/'review-seal.json').read_bytes()),'baselineSourceClosure':seal['baselineSourceClosure'],'baselineCandidateManifestEqual':c.manifest(c.HERE/'baseline')==c.manifest(parent/'baseline'),'records':records,'allCandidateContextsMustBeFresh':True,'runtimeQualified':False})
print('Bound8unchangedbaseline layout pairs and39method expansion evidence')
