from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;S=H/'owned-scratch'
for kind in ('baseline','grouped'):
    p=S/kind/'src/experimental_swift_reactor/cache_tests.rs'
    before=p.read_text();start=before.index('// Diagnosis-only controls on the actual copied cache')
    p.write_text(before[:start]+(H/'controls.rs').read_text())
    original=json.loads((H/'input-source-manifest.json').read_text())
    names={n:hashlib.sha256((S/kind/n).read_bytes()).hexdigest() for n in original}
    (H/(kind+'-final-diagnosis-source-manifest.json')).write_text(json.dumps(names,sort_keys=True,indent=2)+'\n')
(H/'final-ownership-strengthening.json').write_text(json.dumps({'changesOnlyDiagnosisControl':True,'addsExplicitZeroAssertionsForAllSixLiveCategories':True,'productionAndAccountingCleanHandoffUnchanged':True},sort_keys=True,indent=2)+'\n')
