import collect as c
import gzip,json
records=[]
for unit in [False,True]:
 name='private-layout-release-'+('unit' if unit else 'production');code,attempt,out,err=c.run(['cargo','rustc','--lib','--offline','--locked','--features','experimental-swift-reactor','--release','--','--emit=mir','-Zprint-type-sizes']+(['--test'] if unit else []),env_extra={'RUSTC_BOOTSTRAP':'1'},label=name)
 assert code==0
 records.append({'name':name,'attempt':str(attempt.relative_to(c.HERE)),'sourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate')))})
 c.save(c.HERE/'private-layout-attempts.json',records)
