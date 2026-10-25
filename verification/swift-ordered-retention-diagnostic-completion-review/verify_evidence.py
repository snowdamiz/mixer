"""Read archived adversarial fixture links without extracting or following them."""
from pathlib import Path
import gzip,hashlib,json,sys,tarfile
P=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
path=P/'raw-fixtures-manifest.json';manifest=json.loads(path.read_bytes());links=[]
with tarfile.open(P/'raw-fixtures.tar.gz','r:gz') as archive:
    assert len(archive.getmembers())==len(manifest) and sorted(archive.getnames())==sorted(manifest)
    for member in archive:
        info=manifest[member.name]
        if member.issym():
            # These are the intentionally rejected receipt-symlink fixtures.
            # Their target must be one regular archived member in this exact
            # former owned scratch. Never extract or resolve a filesystem link.
            target=str(Path(member.linkname).relative_to(P/'.scratch'));assert '..' not in Path(target).parts
            actual=archive.getmember(target);assert actual.isfile();raw=archive.extractfile(actual).read()
            kind={'type':'symlink','linkname':member.linkname,'archivedTarget':target};links.append(member.name)
        else:
            assert member.isfile();raw=archive.extractfile(member).read();kind={'type':'file'}
        assert len(raw)==info['bytes'] and sha(raw)==info['sha256']
        if sys.argv[1]=='reconcile':info.update(kind)
        else:assert all(info.get(k)==v for k,v in kind.items())
if sys.argv[1]=='reconcile':path.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
binaries=json.loads((P/'binary-manifest.json').read_bytes())
for info in binaries.values():
    zipped=(P/info['archive']).read_bytes();assert sha(zipped)==info['archiveSHA256'];raw=gzip.decompress(zipped);assert len(raw)==info['bytes'] and sha(raw)==info['sha256']
receipt={'rawMembers':len(manifest),'intentionalSymlinks':links,'retainedBinaries':len(binaries),'verified':True,'scratchAbsent':not(P/'.scratch').exists(),'linkTargetsReadOnlyFromArchive':True}
(P/('evidence-'+sys.argv[1]+'.json')).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps(receipt,sort_keys=True))
