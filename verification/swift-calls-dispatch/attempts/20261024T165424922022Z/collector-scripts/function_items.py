"""Separate exact implicit FnDef operands; never alias them to fn pointers."""
import collect as c
import inventory as i
import gzip,re,json
records=[]
for features in ['swift','all']:
 for profile in ['debug','release']:
  for cfg in ['production','unit']:
   context=features+'-'+profile+'-'+cfg;data=gzip.decompress((c.HERE/('preaccounting-'+context+'.mir.gz')).read_bytes());text=data.decode()
   for b in i.blocks(text):
    if i.selection(b) in [None,'fixture-only']:continue
    prior=''
    for ordinal,line in enumerate(b['body'].splitlines()):
     if 'const_: Const { ty: ' in line:
      ty=line.split('const_: Const { ty: ',1)[1].split(', val: ',1)[0]
      if re.search(r'\bfn\([^\n]*\)\s*[^\n]*\{[^\n]+\}$',ty):
       records.append({'context':context,'mirSHA256':c.sha(data),'function':b['name'],'header':b['header'],'bodySHA256':c.sha(b['body'].encode()),'bodyLine':b['line'],'relativeLine':ordinal+1,'actualType':ty,'rawLine':line,'precedingOperand':prior,'status':'exact implicit FnDef identity inventoried; no fn-pointer alias or reservation credit','valueRepresentation':'Function item ZST; inference/layout proof required separately'})
     elif not line.lstrip().startswith('//'):prior=line
c.save(c.HERE/'implicit-function-item-operands.json',records)
print(len(records),'implicit exact FnDef operands;',len({r['actualType']for r in records}),'unique raw types')
