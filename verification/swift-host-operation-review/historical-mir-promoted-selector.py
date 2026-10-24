#!/usr/bin/env python3
from review import *
import collections,re

def sections(data):
 lines=data.decode().splitlines(keepends=True);result=[];i=0
 while i<len(lines):
  line=lines[i]
  if line.startswith('fn ')or line.startswith('const '):
   start=i;i+=1
   while i<len(lines)and lines[i].rstrip()!='}':i+=1
   result.append((line.rstrip(),''.join(lines[start:i+1])) )
  i+=1
 return result

def params(header):
 start=header.index('(')+1;nest=1;end=start
 while nest:
  if header[end]=='(':nest+=1
  if header[end]==')':nest-=1
  end+=1
 text=header[start:end-1];parts=[];depth=0;at=0
 for i,c in enumerate(text):
  if c in '<([{':depth+=1
  elif c in '>)]}':depth-=1
  elif c==','and depth==0:parts.append(text[at:i].strip());at=i+1
 parts.append(text[at:].strip());return [v.split(': ',1)for v in parts if v]

def chosen(header):
 if 'host_operation_tests.rs:'in header:return False
 return any('::'+n+'('in header or header.startswith('fn '+n+'(')or '::'+n+'::'in header for n in ['host_operation','host_operation_inner','host_operation_pinned_caller','host_operation_pinned_step','host_operation_complete'])or ('accounted::'in header and any('::'+n+'('in header or '::'+n+'::'in header for n in ['usage','checked_usage','dispatch','dispatch_checkpoint']))or ('descriptor::'in header and any('::'+n+'('in header or '::'+n+'::'in header for n in ['parameters','results']))

def run():
 schema=json.loads((PACKET/'inventory-schema.json').read_text());manifest=json.loads((PACKET/'function-manifest.json').read_text());results={}
 for config in ['production','unit']:
  original=gzip.decompress((PACKET/('qualified-source-mir-'+config+'.mir.gz')).read_bytes());fresh=gzip.decompress((HERE/('independent-'+config+'.mir.gz')).read_bytes());ob=[x for x in sections(original)if chosen(x[0])];fb=[x for x in sections(fresh)if chosen(x[0])];assert ob==fb,(config,'selected compiler body mismatch');ob=sorted(ob,key=lambda x:x[0].startswith('const '))
  expected_manifest=[r for r in manifest if r['config']==config];assert len(ob)==len(expected_manifest)
  expected_fields=[];body_summaries=[]
  for ordinal,((header,body),saved)in enumerate(zip(ob,expected_manifest)):
   name=header[3:header.index('(')]if header.startswith('fn ')else header[6:]
   assert name==saved['function'],(name,saved['function'])
   bindings=dict(re.findall(r'\blet (?:mut )?(_\d+): ([^\n]+);',body))
   if header.startswith('fn '):bindings.update(params(header))
   aliases=collections.defaultdict(list)
   for alias,binding in re.findall(r'\bdebug ([\w_]+) => (_\d+);',body):aliases[binding].append(alias)
   literals=re.findall(r'\bconst ("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)
   assert (len(bindings),sum(map(len,aliases.values())),len(literals))==(saved['canonicalTypedBindings'],saved['sourceAliases'],saved['directTypedLiterals'])
   for binding,ty in bindings.items():
    stem=f'mir_{config}_{ordinal}_{binding[1:]}'
    for role in ['source','argument','returned','caller']:expected_fields.append((stem+'_'+role,binding,ty,'canonical',role))
    for index,alias in enumerate(aliases[binding]):
     stem=f'alias_{config}_{ordinal}_{binding[1:]}_{index}_{alias}'
     for role in ['source','argument','returned','caller']:expected_fields.append((stem+'_'+role,alias,ty,'authored-alias',role))
   for index,lit in enumerate(literals):
    ty="&'static str"if lit.startswith('"')else'bool'if lit in ['true','false']else lit.rsplit('_',1)[1]
    for role in ['source','argument','returned','caller']:expected_fields.append((f'literal_{config}_{ordinal}_{index}_{role}',f'literal_{index}',ty,'direct-literal',role))
   body_summaries.append(dict(function=name,bodySHA256=sha(body.encode()),canonical=len(bindings),aliases=sum(map(len,aliases.values())),literals=len(literals)))
  actual=[(r['field'],r['binding'],r['mirType'],r['kind'],r['position'])for r in schema if r['config']==config]
  assert expected_fields==actual,(config,len(expected_fields),len(actual),next(((a,b)for a,b in zip(expected_fields,actual)if a!=b),None))
  results[config]=dict(selectedBodies=len(ob),positions=len(actual),allSelectedFreshCompilerBodiesByteIdentical=True,bodies=body_summaries)
 # Each normalized field is a distinct source declaration in its actual measured owner; zero-sized types receive no positive-byte credit.
 text=(scratch()/'candidate/src/experimental_swift_reactor/frame_operations.rs').read_text()
 for r in schema:assert text.count('    '+r['field']+': '+r['rustType']+',')==1,r['field']
 fixed=[r for r in schema if r['config']=='source'];assert len(fixed)==44 and len({r['binding']for r in fixed})==11
 assert results['production']['positions']==2344 and results['unit']['positions']==2488
 results['fixedPositions']=44;results['totalPositions']=4876;results['everyNamedFieldDeclaredExactlyOnce']=True
 unit_zero=[r['field']for r in schema if r['config']=='unit'and r['binding']=='_0'and r['mirType']=='()'];assert len(unit_zero)==4
 results['unitReturnEmptyIntervals']=unit_zero;results['zeroSizedFieldsReceiveNoPositiveByteCredit']=True
 save('mir-audit.json',results);print('Independent fresh MIR inventory passed: 2344 + 2488 + 44 = 4876 positions',flush=True)
if __name__=='__main__':run()
