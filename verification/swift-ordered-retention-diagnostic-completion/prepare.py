"""Prepare only approved complete copied sources; never mutates the live VM."""
from pathlib import Path
import hashlib, json, tarfile, difflib, datetime

P = Path(__file__).resolve().parent
R = P.parents[1]
O = P.parent / 'swift-ordered-retention-diagnostic-rust'
S = P / '.scratch'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def dump(path, obj): path.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
def verify_original():
    assert sha((O/'seal.json').read_bytes()) == 'c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf'
    seal = json.loads((O/'seal.json').read_bytes())
    assert len(seal['members']) == 186
    for item in seal['members']:
        f=R/item['path']; raw=f.read_bytes()
        assert f.is_file() and not f.is_symlink() and len(raw)==item['bytes'] and sha(raw)==item['sha256'], item['path']
def manifest(root, names): return {n:sha((root/n).read_bytes()) for n in names}
def freeze():
    base=json.loads((O/'baseline-source-manifest.json').read_bytes())
    for label in ('baseline','candidate'):
        files=manifest(S/label,base)
        dump(P/(label+'-manifest.json'),files)
        with tarfile.open(P/(label+'-source.tar.gz'),'w:gz') as archive:
            for n in base: archive.add(S/label/n,arcname=n,recursive=False)
    before=manifest(S/'baseline',base); after=manifest(S/'candidate',base)
    changed=[n for n in base if before[n]!=after[n]]
    assert changed==[n for n in base if n in {
        'src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs',
        'src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/control.rs'}]
    text=[]
    for n in changed:
        text.extend(difflib.unified_diff((S/'baseline'/n).read_text().splitlines(True),
            (S/'candidate'/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
    (P/'candidate.patch').write_text(''.join(text))
    original=json.loads((O/'candidate-manifest.json').read_bytes())
    delta=[n for n in base if original[n]!=after[n]]
    assert delta==['src/experimental_swift_reactor/cache_tests.rs'],delta
    dump(P/'completion-delta.json',{'changedFromOriginalCandidate':delta,'copiedChangesFromPristine':changed})
def main():
    verify_original()
    base=json.loads((O/'baseline-source-manifest.json').read_bytes())
    assert len(base)==132 and manifest(R/'vm',base)==base
    S.mkdir(exist_ok=False); owned={}
    st=S.stat(); owned['.']={'dev':st.st_dev,'ino':st.st_ino}
    for name in ('baseline','candidate','build-baseline','build-candidate','tmp-baseline','tmp-candidate'):
        d=S/name; d.mkdir(); st=d.stat(); owned[name]={'dev':st.st_dev,'ino':st.st_ino}
    dump(P/'scratch-ownership.json',owned)
    for label in ('baseline','candidate'):
        source=json.loads((O/(label+'-manifest.json')).read_bytes())
        with tarfile.open(O/(label+'-source.tar.gz'),'r:gz') as archive:
            assert sorted(archive.getnames())==sorted(base)
            for item in archive:
                assert item.isfile() and item.name in source
                raw=archive.extractfile(item).read(); assert sha(raw)==source[item.name]
                f=S/label/item.name; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(raw)
    f=S/'candidate/src/experimental_swift_reactor/cache_tests.rs'
    f.write_bytes(f.read_bytes()+b'\n'+(P/'completion_tests.rs').read_bytes())
    (P/'baseline-source-manifest.json').write_bytes((O/'baseline-source-manifest.json').read_bytes())
    freeze()
    dump(P/'preparation.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'closureFiles':132,'originalPacketUnchanged':True,'live132Unchanged':True,
        'scope':'approved copied fixture completion, no target/native/process discovery'})
    print('prepared complete pristine/candidate copies; completion delta cache_tests.rs only')
if __name__=='__main__': main()
