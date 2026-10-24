#!/usr/bin/env python3
"""Compile four real MIR configurations and replay every positive role."""
from pathlib import Path
import collections,gzip,json,re
from run import run,SCRATCH,HERE,b
import inventory

def function_identity(name):
 name=name.removeprefix('experimental_swift_reactor::execution::frame_operations::')
 return name.removeprefix('memory_operations::') if name.startswith('memory_operations::memory_pinned') else name

def type_identity(ty):
 return re.sub(r'(?<![:\w])control::','experimental_swift_reactor::control::',ty.replace('crate::',''))

def role(row):
 return (function_identity(row['mirFunction']),row['field'],row['binding'],row['kind'],tuple(row['sourceNames']),row['position'],type_identity(row['mirType']))

def validate(path,config,schema):
 rows,defs,captures=inventory.canonical(path,config)
 actual=collections.Counter(role(r) for r in rows)
 expected=collections.Counter(role(r) for r in schema if r['config']==config)
 assert actual==expected,(config,list((actual-expected).items())[:3],list((expected-actual).items())[:3])
 assert len(defs)==(22 if config=='unit' else 21)
 assert sum('::promoted[' in d['function'] for d in defs)==(3 if config=='unit' else 2)
 assert len(captures)==5
 return dict(config=config,canonicalBodies=len(defs),positiveCanonicalFields=len(rows),definitions=defs,captures=captures,exactPositiveRoles=True,mirSHA256=b.sha(path))

def main():
 schema=json.loads((HERE/'inventory-schema.json').read_text());audit=[]
 for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for unit in [False,True]:
   config='unit' if unit else 'production';name='canonical-'+feature+'-'+config+'-mir';extra={'RUSTC_BOOTSTRAP':'1'}
   if unit:
    argv=['cargo','test','--lib','--no-run','--locked','--offline',*flags];extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
   else:argv=['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']
   p=run(name,argv,SCRATCH/'candidate/vm',extra);assert p.returncode==0
   files=[p for p in (SCRATCH/('target-'+name)/'debug/deps').glob('*.mir') if '::memory_operation(' in p.read_text()];assert len(files)==1,files
   path=HERE/('canonical-'+feature+'-'+config+'.mir.gz');path.write_bytes(gzip.compress(files[0].read_bytes(),mtime=0))
   row=validate(path,config,schema);row.update(feature=feature,command=name,sourceClosure=b.digest(b.manifest(SCRATCH/'candidate/vm')),uncompressedMirSHA256=b.sha(files[0]))
   audit.append(row);(HERE/'canonical-audit.json').write_bytes(b.enc(audit))
   if feature=='all':(HERE/('canonical-'+config+'.mir.gz')).write_bytes(path.read_bytes())
 assert len(audit)==4
 print('four actual compiler MIR configurations exactly reproduce all positive schema roles',flush=True)

if __name__=='__main__':main()
