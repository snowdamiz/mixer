#!/usr/bin/env python3
"""Compare full compiler layouts of every original emitted owned type."""
import gzip,json,re
import collect as c

def parse(text):
 result={};current=None
 for line in text.splitlines():
  m=re.fullmatch(r'print-type-size type: `(.+)`: (\d+) bytes, alignment: (\d+) bytes',line)
  if m:
   current=m[1];result[current]={'bytes':int(m[2]),'alignment':int(m[3]),'detail':[]}
  elif line.startswith('print-type-size ')and current is not None:
   result[current]['detail'].append(line.removeprefix('print-type-size '))
 return result

def main():
 records=[]
 for features in ['swift','all']:
  for profile in ['debug','release']:
   for config in ['production','unit']:
    rows={}
    for label in ['baseline','candidate']:
     name='build-qualified-'+label+'-'+features+'-'+profile+'-'+config
     text=''.join(gzip.decompress((c.HERE/'commands'/name/(s+'.gz')).read_bytes()).decode()for s in ['stdout','stderr'])
     rows[label]=parse(text)
    before={k:v for k,v in rows['baseline'].items()if k.startswith(('experimental_swift_reactor::','experimental_wasi::'))}
    assert before
    layouts={}
    for name,layout in before.items():
     assert rows['candidate'].get(name)==layout,(features,profile,config,name)
     v=dict(layout);offset=0;fields={}
     # Rustc emits struct fields in memory order and explicit padding. Enum
     # details are retained byte-for-byte rather than guessed across variants.
     if not any('variant `'in line for line in v['detail']):
      for line in v['detail']:
       m=re.fullmatch(r'    field `\.([^`]+)`: (\d+) bytes(?:.*)',line)
       if m:fields[m[1]]={'offset':offset,'bytes':int(m[2])};offset+=int(m[2]);continue
       m=re.fullmatch(r'    (?:end )?padding: (\d+) bytes(?:.*)',line)
       if m:offset+=int(m[1])
      if fields:assert offset==v['bytes'],(name,offset,v['bytes'],v['detail'])
      v['fields']=fields
     layouts[name]=v
    records.append({'features':features,'profile':profile,'config':config,'unchangedOwnedTypes':len(layouts),'layouts':layouts})
 c.save('complete-owned-type-layout-replay.json',{'pairedContexts':len(records),'records':records,'basis':'actual final rustc -Zprint-type-sizes; identical full original layout details, explicit struct field offsets; enum variant detail retained exact','metadataOverlayOnly':True})
 print('Full original owned layouts equal in',len(records),'pairs;',[(r['config'],r['unchangedOwnedTypes'])for r in records])
if __name__=='__main__':main()
