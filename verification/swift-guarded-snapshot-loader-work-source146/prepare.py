"""Read-only frozen source/custody reconstruction; writes only this preparation."""
import datetime,difflib,gzip,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
OLD=V/'swift-guarded-snapshot-loader-work';FIX=V/'swift-guarded-snapshot-loader-work-correction'
COMP=V/'swift-guarded-snapshot-host-composition';IND=V/'swift-guarded-snapshot-host-composition-independent'
BASE=V/'swift-guarded-snapshot-funding-implementation/source/vm';OLDOVER=V/'swift-guarded-snapshot-descriptor-rebinding/overlay/vm';OVER=COMP/'overlay/vm'
ACCEPT=V/'swift-semantic-adapter-root-review/guarded-snapshot-host-composition-host-acceptance.json'
EXPECTED_TREE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,v):(D/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def verify_seal(folder,digest,count):
 b=(folder/'seal.json').read_bytes();assert sha(b)==digest
 j=json.loads(b);assert j['member_count']==len(j['members'])==count
 total=0
 for row in j['members']:
  p=folder/row['path'];assert not p.is_symlink();data=p.read_bytes()
  assert len(data)==row['bytes'] and sha(data)==row['sha256'],str(p);total+=len(data)
 return dict(path=str(folder.relative_to(R)),seal_sha256=digest,members_verified=count,bytes_verified=total)
def reconstruct(manifest,overlay):
 rows=manifest['members'];result={};refs={}
 for row in rows:
  p=overlay/row['path'] if (overlay/row['path']).exists() else BASE/row['path'];b=p.read_bytes()
  assert sha(b)==row['sha256'] and len(b)==row['bytes'],str(p)
  result[row['path']]=b;refs[row['path']]=str(p.relative_to(R))
 assert sha(canonical(rows))==manifest['tree_sha256']
 return result,refs

def inputs():
 ab=ACCEPT.read_bytes();assert sha(ab)=='c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8'
 custody=[verify_seal(COMP,'2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e',152),verify_seal(IND,'c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63',96),verify_seal(OLD,'0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c',46),verify_seal(FIX,'b7142125a8b00f0fbf9ade17d2c7697e42c1ef20d972a995dddfd452e92eff4e',28)]
 oldm=json.loads((OLD/'compiler-source-manifest.json').read_text());newm=json.loads((COMP/'source-manifest.json').read_text());assert newm['member_count']==146 and newm['tree_sha256']==EXPECTED_TREE
 old,oldrefs=reconstruct(oldm,OLDOVER);new,newrefs=reconstruct(newm,OVER)
 hosts=json.loads((COMP/'host-support-manifest.json').read_text());assert len(hosts['members'])==11 and hosts['tree_sha256']=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
 assert sha(canonical(hosts['members']))==hosts['tree_sha256']
 for row in hosts['members']:
  b=(V/'swift-real-profile-loader-binding/host'/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
 return old,new,oldrefs,newrefs,oldm,newm,hosts,custody

def main():
 old,new,oldrefs,newrefs,oldm,newm,hosts,custody=inputs()
 delta=[];patch=''
 for p in sorted(set(old)|set(new),key=Path):
  before=old.get(p);after=new.get(p)
  if before!=after:
   delta.append(dict(path=p,old=dict(bytes=len(before),sha256=sha(before),read_from=oldrefs[p]) if before is not None else None,new=dict(bytes=len(after),sha256=sha(after),read_from=newrefs[p]) if after is not None else None))
   patch+=''.join(difflib.unified_diff((before or b'').decode().splitlines(True),(after or b'').decode().splitlines(True),fromfile='quoted-source145/'+p,tofile='accepted-source146/'+p))
 (D/'source145-to-source146.patch').write_text(patch)
 body=json.loads((OLD/'source-body-ledger.json').read_text());changed=[];same=[]
 for name,row in body['nodes'].items():
  s=row['source'];path=s['path'].split('/vm/',1)[1];lines=old[path].splitlines(True);span=b''.join(lines[s['line']-1:s['end_line']])
  # Match the frozen byte-length fingerprint at its exact first-line offset;
  # pub/unsafe qualifiers differ among functions and are never guessed away.
  offsets=[i for i in range(len(lines[s['line']-1])) if sha(span[i:i+s['bytes']])==s['sha256']]
  assert len(offsets)==1,(name,offsets)
  start=offsets[0];excerpt=span[start:start+s['bytes']]
  newspan=b''.join(new[path].splitlines(True)[s['line']-1:s['end_line']]);candidate=newspan[start:start+s['bytes']]
  result=dict(name=name,path=path,old_sha256=s['sha256'],new_sha256=sha(candidate),line=s['line'],end_line=s['end_line'],bytes=s['bytes'])
  (same if excerpt==candidate else changed).append(result)
 assert [r['name'] for r in changed]==['build'],changed
 loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
 assert old[loader].replace(b'word(b, 32) != 145',b'word(b, 32) != 146')==new[loader]
 put('source-comparison.json',dict(schema=1,source145_tree_sha256=oldm['tree_sha256'],source146_tree_sha256=newm['tree_sha256'],old_members=145,new_members=146,old_bytes=sum(map(len,old.values())),new_bytes=sum(map(len,new.values())),unchanged_members=len(set(old)&set(new))-sum(1 for r in delta if r['old'] is not None),delta=delta,selected_source_bodies=129,body_unchanged=len(same),body_changed=changed,unchanged_bodies=same,only_selected_body_change='parse_build distribution-count literal145->146'))
 put('source146-manifest.json',newm);put('host11-manifest.json',hosts)
 put('source-reference-map.json',dict(schema=1,members=[dict(path=p,source=newrefs[p],bytes=len(new[p]),sha256=sha(new[p])) for p in sorted(new,key=Path)]))
 put('input-bindings.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),acceptance=dict(path=str(ACCEPT.relative_to(R)),sha256=sha(ACCEPT.read_bytes())),packets=custody,source146_tree_sha256=newm['tree_sha256'],host11_tree_sha256=hosts['tree_sha256'],old_correction_review_pending=True,no_original_script_import_or_replay=True))
 # Frozen source146 MIR is complete for the named19-function account/entry
 # subset only. It is useful overlap evidence, never a substitute for loader219.
 archive=json.loads((IND/'entry-and-account.mir-archive.json').read_text());mir=gzip.decompress((IND/'entry-and-account.mir.gz').read_bytes());assert sha(mir)==archive['raw_sha256']
 heads=[x for x in mir.decode().splitlines() if x.startswith('fn ')]
 put('existing-MIR-availability.json',dict(schema=1,producer_subset=dict(path=str((COMP/'entry-and-account.mir').relative_to(R)),bytes=(COMP/'entry-and-account.mir').stat().st_size,sha256=sha((COMP/'entry-and-account.mir').read_bytes())),independent_subset=dict(path=str((IND/'entry-and-account.mir.gz').relative_to(R)),raw_bytes=len(mir),raw_sha256=sha(mir),functions=len(heads),archive_sha256=archive['archive_sha256']),full_loader219_MIR_retained=False,reason='accepted152/96-member seals retain account/entry subset; whole-source MIR removed with recorded owned scratch cleanup',root_authorized_new_exclusive_compile=True))
 print(json.dumps(dict(status='source146-prepared',members=146,selected_bodies_same=len(same),selected_bodies_changed=len(changed),changed_members=len(delta),existing_subset_functions=len(heads))))
if __name__=='__main__':main()
