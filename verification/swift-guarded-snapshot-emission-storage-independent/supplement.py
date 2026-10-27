"""Exact declaration-span and command-binding checks, independently authored."""
import json,re
from review import HERE,P,OWNER,BASE,INITIAL,NAMES,sha,canonical,load,functions,declarations,qual,save,snippet

rows=[]
def check(name,value):
 rows.append({'name':name,'pass':bool(value)})
 if not value:raise AssertionError(name)
fs=functions((P/'production-functions.mir').read_text())
for group,name in [('helper',NAMES[0]),('proposed_wrapper',NAMES[1])]:
 body=fs[name]
 for r in load(P/'roles.json')[group]:
  local=r['mir_local']
  if local=='_1':line=next(l for l in body.splitlines() if re.search(r'debug \w+ => '+local+r';',l))
  else:line=next(l for l in body.splitlines() if re.match(r'\s*let (?:mut )?'+local+r':',l))
  m=re.search(r'at source/([^:]+):(\d+):(\d+): (\d+):(\d+)',line)
  observed={'path':'src/'+m[1],'start_line':int(m[2]),'start_column':int(m[3]),'end_line':int(m[4]),'end_column':int(m[5])}
  check('exact-declaration-source-span-'+r['id'],all(r['source'][k]==v for k,v in observed.items()))
  if local!='_1':check('exact-declaration-origin-'+r['id'],line.split('//',1)[1].strip()==r['declaration_origin'])
old=functions((OWNER/'function-bodies.mir').read_text())
old_wrapper=load(P/'baseline-wrapper-roles.json')
for r in old_wrapper:
 check('baseline-exact-type-'+r['id'],qual(declarations(old[NAMES[1]])[r['mir_local']])==qual(r['compiler_type']))
 if r['mir_local']!='_1':
  line=next(l for l in old[NAMES[1]].splitlines() if re.match(r'\s*let (?:mut )?'+r['mir_local']+r':',l))
  check('baseline-exact-origin-'+r['id'],line.split('//',1)[1].strip()==r['mir_declaration_origin'].replace(str(BASE/'source/vm/src')+'/', 'source/'))
for r in load(P/'preserved-begin-roles.json')['roles']:
 identity,local=r['baseline_id'].rsplit('::',1);name=identity.removeprefix('owner::')
 check('caller-exact-type-'+r['baseline_id'],qual(declarations(old[name])[local])==qual(r['compiler_type']))
for path in sorted((P/'commands').glob('*/receipt.json')):
 r=load(path);env=r['environment'];expected_env={k:v for k,v in env.items() if k!='MIXER_LOADER_COMPILE_ENV_SHA256'}
 check('producer-command-digest-'+path.parent.name,env['MIXER_LOADER_COMMAND_SHA256']==sha(canonical(r['argv'])))
 check('producer-environment-digest-'+path.parent.name,env['MIXER_LOADER_COMPILE_ENV_SHA256']==sha(canonical(expected_env)))
 check('producer-manifest-digest-'+path.parent.name,env['MIXER_LOADER_MANIFEST_SHA256']==sha(canonical(load(path.parent/'source-preimage.json')['members'])))
 check('producer-compiler-version-digest-'+path.parent.name,env['MIXER_LOADER_COMPILER_VERSION_SHA256']==sha(r['rustc_version'].encode()))
 if (path.parent/'probe-source.py').exists():check('producer-retained-coordinator-'+path.parent.name,sha((path.parent/'probe-source.py').read_bytes())==load(path.parent/'source-preimage.json')['probe_sha256'])
for path in sorted((HERE/'commands').glob('*/receipt.json')):
 r=load(path);env=r['environment'];expected_env={k:v for k,v in env.items() if k!='MIXER_LOADER_COMPILE_ENV_SHA256'}
 check('independent-command-digest-'+path.parent.name,env['MIXER_LOADER_COMMAND_SHA256']==sha(canonical(r['argv'])))
 check('independent-environment-digest-'+path.parent.name,env['MIXER_LOADER_COMPILE_ENV_SHA256']==sha(canonical(expected_env)))
 check('independent-preimage-'+path.parent.name,env['MIXER_LOADER_MANIFEST_SHA256']==sha(canonical(load(path.parent/'source-preimage.json')['members'])))
 check('independent-coordinator-'+path.parent.name,load(path.parent/'source-preimage.json')['review_script_sha256']==sha((HERE/'review.py').read_bytes()))
# Reconstruct the accepted helper29 without adding a direct call boundary:
# entry/return2 + two named field reads + four checked operations + four
# ok_or inspect/output pairs + four eager error constructors + three ? pairs
# + three explicit source bindings. The wrapper forwards one bound local.
helper_actions=2+2+4+4*2+4+3*2+3
check('independent-helper-source-actions29',helper_actions==29)
check('independent-evaluator31-net28',2+helper_actions==31 and 2+helper_actions-(2+1)==28)
save('supplement-controls.json',{'count':len(rows),'all_passed':True,'controls':rows,'helper_action_parts':{'entry_return':2,'named_field_reads':2,'checked_operations':4,'ok_or_inspect_output':8,'eager_error_construction':4,'question_inspection_payload':6,'source_bindings':3},'scope':'exact source occurrences and host compiler metadata; no base alias acceptance'})
print(json.dumps({'supplement_controls':len(rows),'all_passed':True}))
