import collect as c
import gzip,json,re

def main():
 records=[]
 for features in ['swift','all']:
  for profile in ['debug','release']:
   for unit in [False,True]:
    name=features+'-'+profile+'-'+('unit' if unit else 'production')
    flags=['--no-default-features']+(['--features','experimental-swift-reactor'] if features=='swift' else ['--all-features'])+(['--release'] if profile=='release' else [])
    argv=['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']+(['--test'] if unit else [])
    code,attempt,out,err=c.run(argv,env_extra={'RUSTC_BOOTSTRAP':'1'},label='preaccounting-mir-'+name)
    assert code==0
    artifacts=json.loads((attempt/'artifacts.json').read_text());mirs=[x for x in artifacts if x['path'].endswith('.mir.gz')];assert len(mirs)==1
    data=gzip.decompress((attempt/mirs[0]['path']).read_bytes());c.save(c.HERE/('preaccounting-'+name+'.mir.gz'),gzip.compress(data,mtime=0))
    records.append({'name':name,'attempt':str(attempt.relative_to(c.HERE)),'mir':mirs[0],'sourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate')))})
    c.save(c.HERE/'preaccounting-mir-contexts.json',records)
 print('Eight complete candidate MIR contexts captured')
if __name__=='__main__':main()
