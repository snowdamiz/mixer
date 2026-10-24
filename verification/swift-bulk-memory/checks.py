from run import run,SCRATCH,HERE,b
results=[]
for features,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in[False,True]:
  name='sealed-library-'+features+('-release'if release else'-debug');p=run(name,['cargo','check','--lib','--locked','--offline',*flags,*(['--release']if release else[])],SCRATCH/'candidate');assert p.returncode==0;results.append(name)
p=run('sealed-ci-swift-clippy',['cargo','clippy','--lib','--locked','--offline','--features','experimental-swift-reactor','--','-D','warnings'],SCRATCH/'candidate');assert p.returncode==0
(HERE/'library-checks.json').write_bytes(b.enc(dict(libraryChecks=results,swiftCIClippy=True)))
for name,args in [('rustc-version',['rustc','--version','--verbose']),('cargo-version',['cargo','--version']),('python-version',['python3','--version']),('host-version',['uname','-a'])]:assert run(name,args,SCRATCH/'candidate').returncode==0
