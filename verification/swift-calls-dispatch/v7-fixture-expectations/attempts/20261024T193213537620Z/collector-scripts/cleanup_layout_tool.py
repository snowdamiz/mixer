import collect as c
from pathlib import Path
import json,subprocess,shutil,gzip
s=c.read_json(c.HERE/'layout-tool-session.json');scratch=Path(s['scratch']);assert scratch.name.startswith('mixer-calls-exact-layout-tool-')and scratch.is_dir();prep=c.HERE/s['preparation']
added=c.read_json(prep/'added-component-files.json');original=c.read_json(prep/'original-sysroot-bindings.json');base=Path(c.read_json(c.HERE/c.read_json(c.HERE/'layout-driver-build.json')['attempt']/'tools.json')['actualCompiler']['sysroot'])
for rel,sha in added.items():assert c.sha((Path(s['sysroot'])/rel).read_bytes())==sha,rel
for rel,sha in original.items():assert c.sha((base/rel).read_bytes())==sha,rel
build=c.read_json(c.HERE/'layout-driver-build.json');assert c.sha(Path(build['binary']).read_bytes())==build['sha256'];assert c.sha(gzip.decompress((c.HERE/build['attempt']/'layout-driver.gz').read_bytes()))==build['sha256']
holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True);c.save(prep/'final-holders.log',holders.stdout+holders.stderr);assert holders.returncode==1 and not holders.stdout and not holders.stderr
files=[p for p in scratch.rglob('*')if p.is_file()];count=len(files);size=sum(p.stat().st_size for p in files)
shutil.rmtree(scratch)
c.save(prep/'final-cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'holderCheckEmpty':True,'holderReturnCode':holders.returncode,'holderStdoutEmpty':not holders.stdout,'holderStderrEmpty':not holders.stderr,'logicalFilesRemoved':count,'logicalBytesRemoved':size,'allAddedOfficialComponentFileHashesVerified':len(added),'allOriginalCompilerCriticalFileHashesUnchanged':len(original),'driverSourceAndExecutablePreserved':True,'driverSHA256':build['sha256'],'sharedToolchainInstalledOrConfigured':False,'productRuntimeExcluded':True,'nativeInstancesCreated':0})
print('Owned exact-layout compiler scratch removed after complete byte verification and capture')
