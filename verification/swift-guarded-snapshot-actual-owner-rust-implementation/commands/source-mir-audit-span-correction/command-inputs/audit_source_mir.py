"""Complete MIR item inventory plus exact source custody; no native authority."""
from pathlib import Path
import collections,gzip,hashlib,json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,j):p.write_text(json.dumps(j,sort_keys=True,indent=2)+'\n')
def row(p,base=HERE):
 b=p.read_bytes();return dict(path=str(p.relative_to(base)) if p.is_relative_to(base) else str(p),bytes=len(b),sha256=sha(b))
def strip_comment(line):
 quoted=False;escaped=False
 for i,c in enumerate(line):
  if escaped:escaped=False;continue
  if c=='\\' and quoted:escaped=True;continue
  if c=='"':quoted=not quoted
  if not quoted and line[i:i+2]=='//':return line[:i].rstrip()
 return line.rstrip()
def normalized(raw):
 # Keep every MIR operation, place, literal, scalar, type, CFG edge, drop and
 # allocation byte. Remove ONLY rustc display comments/impl span coordinates.
 lines=[]
 for line in raw.splitlines():
  value=strip_comment(line)
  if not value.strip():continue
  value=re.sub(r'(<impl at [^>]+?\.rs):\d+:\d+: \d+:\d+>',r'\1:SPAN>',value)
  value=re.sub(r'(\{closure@[^}]+?\.rs):\d+:\d+: \d+:\d+}',r'\1:SPAN}',value)
  lines.append(value)
 return '\n'.join(lines)
def items(raw):
 output=[];current=[];kind=None;ordinal=collections.Counter()
 for line in raw.splitlines(keepends=True):
  start=None
  if line.startswith('fn '):start='fn'
  elif line.startswith('const '):start='const'
  elif line.startswith('static '):start='static'
  elif re.match(r'^alloc\d+(?: |\t|\()',line):start='alloc'
  elif line and not line[0].isspace() and line.rstrip().endswith(' = {') and ': ' in line:start='standalone_const'
  elif line and not line[0].isspace() and not line.startswith(('//','}','\n')):
   raise AssertionError(('unknown top-level MIR syntax',line[:120]))
  if start is not None:
   if current:output.append((kind,''.join(current)))
   kind=start;current=[line]
  elif current:current.append(line)
  elif line.strip() and not line.startswith('//'):raise AssertionError('unaccounted MIR prefix')
 if current:output.append((kind,''.join(current)))
 result=[]
 for kind,body in output:
  header=normalized(body.splitlines()[0]);ordinal[(kind,header)]+=1
  result.append(dict(kind=kind,header=header,occurrence=ordinal[(kind,header)],raw_sha256=sha(body.encode()),normalized_sha256=sha(normalized(body).encode()),bytes=len(body.encode())))
 return result
if __name__=='__main__':
 custody=json.loads((ROOT/'verification/swift-guarded-snapshot-owned-binding-provider/proposed-source-custody.json').read_text())
 members=[];changed=[]
 for old in custody:
  p=HERE/'source/vm'/old['path'];r=row(p,HERE/'source/vm');members.append(r)
  if r['sha256']!=old['sha256']:changed.append(old['path'])
 assert len(members)==146 and changed==['src/experimental_swift_reactor/cache/initial_profile_v1.rs','src/experimental_swift_reactor/retained_profile_loader_v1.rs'],changed
 host=json.loads((ROOT/'verification/swift-guarded-snapshot-host-composition/host-support-manifest.json').read_text())
 assert [row(HERE/'source/host'/r['path'],HERE/'source/host') for r in host['members']]==host['members']
 loader=HERE/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs';oldloader=next(r for r in custody if r['path'].endswith('/retained_profile_loader_v1.rs'))
 original=(ROOT/oldloader['origin']).read_bytes();assert loader.read_bytes().startswith(original)
 account=next(r for r in custody if r['path'].endswith('/host_account_v1.rs'));assert row(HERE/'source/vm'/account['path'],HERE/'source/vm')['sha256']==account['sha256']
 text=loader.read_text();assert text.index('    drop(executable);')<text.index('    let input = retained(',text.index('    drop(executable);'))<text.index('    let validation = validate_swift_reactor',text.index('    drop(executable);'))
 for forbidden in ['from_raw_fd','transmute','Box::leak','mem::forget']:
  assert forbidden not in text.split('// Actual private ownership core.')[1]
 raw=(HERE/'build/actual.mir').read_text();allitems=items(raw)
 before=gzip.decompress((HERE/'commands/production/full.mir.gz').read_bytes()).decode();olditems=items(before)
 assert len(allitems)==len(olditems)
 changed_mir=[]
 for i,(a,b) in enumerate(zip(olditems,allitems)):
  assert (a['kind'],a['header'],a['occurrence'])==(b['kind'],b['header'],b['occurrence']),(i,a['header'],b['header'])
  if a['normalized_sha256']!=b['normalized_sha256']:changed_mir.append(dict(index=i,kind=a['kind'],header=a['header'],before=a['normalized_sha256'],after=b['normalized_sha256']))
 # Every source change between these exact compiles is inside cfg(test); all
 # non-allocation item bodies must agree after display span normalization.
 assert all(r['kind']=='alloc' for r in changed_mir),changed_mir[:4]
 required=['read_owned_body_once_v1','read_preowned_file_set_once_v1','verify_actual_bodies_core_v1','derive_provenance_v1','correlate_core_v1','correlate_admitted_loader_v1','retire_acquired_owner_core_v1','run_prepaid_admitted_fixture_v1','consume_admitted_owner_once_v1']
 for name in required:assert any(name in r['header'] and r['kind']=='fn' for r in allitems),name
 assert 'InputBridgeV1<File>' in raw or 'InputBridgeV1<std::fs::File>' in raw
 write(HERE/'final-source-manifest.json',dict(schema=1,member_count=146,members=members,tree_sha256=sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),changed=changed))
 write(HERE/'mir-inventory.json',dict(schema=1,input=row(HERE/'build/actual.mir'),complete_item_count=len(allitems),counts=dict(collections.Counter(r['kind'] for r in allitems)),items=allitems))
 write(HERE/'mir-comparison.json',dict(schema=1,before_input=row(HERE/'commands/production/full.mir.gz'),final_input=row(HERE/'build/actual.mir'),full_item_count=len(allitems),scope='complete pre/post test-only repair MIR inventory; all non-allocation production items unchanged after display comments/spans; every original loader source byte separately preserved',changed_mir=changed_mir,required_functions=required,actual_File_specialization_typechecked=True,original_loader_full_prefix_bytes=len(original),original_loader_full_prefix_sha256=sha(original),new_layout_or_work_price=False,baseline_146_complete_MIR_available=False,native_release_authority=False))
 print(json.dumps(dict(source146=len(members),changed=changed,host11_unchanged=True,full_MIR_items=len(allitems),counts=dict(collections.Counter(r['kind'] for r in allitems)),changed_allocation_items=len(changed_mir),original_loader_prefix_exact=True,File_specialization=True)))
