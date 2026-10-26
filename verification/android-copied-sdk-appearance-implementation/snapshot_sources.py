import hashlib,json,pathlib,shutil
BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
paths=set()
for folder in ['cli/Sources','cli/Tests','cli/build-tests','sdk/Sources','updates/Sources']:
    paths.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for name in ['cli/Package.swift','cli/Package.resolved','sdk/Package.swift','updates/Package.swift','updates/Package.resolved','contracts/ui-v1.json']:
    if (ROOT/name).is_file():paths.add(ROOT/name)
p=json.loads((ROOT/'verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json').read_text())
for relative in p['adapter_files']:
    paths.add(ROOT/'native/android'/('engine/'+relative if relative.startswith('Sources/') else relative))
rows={}
for path in sorted(paths):
    relative=path.relative_to(ROOT).as_posix();data=path.read_bytes()
    rows[relative]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    target=BASE/'source-inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
records=''.join(path+'\0'+row['sha256']+'\n' for path,row in sorted(rows.items())).encode()
result={'schema':1,'source_revision':'559858810e133640d52730972a6610e98442be6d','scope':'Final first-party CLI/host-test/SDK/update sources, explicit adapter map, package pins, separately pinned UI wire specification; no hosted catalog or WorkerV2 input.', 'tree_sha256':hashlib.sha256(records).hexdigest(),'files':rows}
(BASE/'source-binding.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print('Source binding:',len(rows),'files',result['tree_sha256'])
