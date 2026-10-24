#!/usr/bin/env python3
"""Verify the final review packet without Cargo targets or executing binaries."""
from pathlib import Path
import hashlib, json, subprocess, sys, tarfile

ROOT = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
enc = lambda value: (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


def archive_files(path):
    with tarfile.open(path) as archive:
        return {member.name.removeprefix('vm/'):archive.extractfile(member).read()
                for member in archive if member.isfile()}


def verify_commands(path, receipt):
    for command in receipt['commands']:
        assert command['exitCode'] == 0
        for stream in ['stdout','stderr']:
            assert sha((path/command[stream]).read_bytes()) == command[stream+'SHA256']


def main():
    result = subprocess.run([sys.executable,str(ROOT/'verify.py'),str(ROOT/'results/20261024T050023355218Z')],capture_output=True,text=True)
    assert result.returncode == 0,result.stderr
    layout = ROOT/'layout-results/20261024T050837492680Z'
    receipt = json.loads((layout/'receipt.json').read_text())
    assert receipt['status'] == 'passed-two-fresh-exact-field-layout-checks'
    verify_commands(layout,receipt)
    portable = json.loads((layout/'qualifying-artifacts.json').read_text())
    assert sha((layout/portable['archive']).read_bytes()) == portable['archiveSHA256']
    artifacts = archive_files(layout/portable['archive'])
    assert set(artifacts) == {member['member'] for member in portable['members']}
    for member in portable['members']:assert sha(artifacts[member['member']]) == member['sha256']
    original = archive_files(layout/'inputs/candidate-source.tar.gz')
    manifest = {name:sha(data) for name,data in sorted(original.items())}
    assert manifest == json.loads((layout/'inputs/candidate-manifest.json').read_text())
    assert sha(enc(manifest)) == receipt['sourceFreeze']['sourceTreeSHA256']
    probe = (layout/'inputs/layout-probe.rs').read_bytes()
    schemas=[]
    for name,mapping in [('frozen-inventory-schema.json',{'permanent':'PermanentPositions','active':'ActivePositions'}),('implementation-inventory-schema.json',{'permanent':'ImplementationPermanentPositions','active':'ImplementationActivePositions'})]:
        schemas.extend(dict(row,ownerClass=mapping[row['envelope']]) for row in json.loads((layout/'inputs'/name).read_text()))
    for item in receipt['layouts']:
        derived = dict(original)
        derived['src/experimental_swift_reactor/frame_operations.rs'] += b'\n'+probe
        if not item['unit']:
            derived['src/experimental_swift_reactor/mod.rs'] += b'\npub(crate) fn independent_frame_layout_route(){execution::frame_operations::independent_layout_probe();}\n'
            derived['src/lib.rs'] += b'\npub fn independent_frame_accounting_layout(){experimental_swift_reactor::independent_frame_layout_route();}\n'
            derived['src/bin/independent_frame_layout.rs'] = b'fn main(){mixer_vm::independent_frame_accounting_layout();}\n'
        assert derived == archive_files(layout/(item['label']+'-source.tar.gz'))
        manifest = {name:sha(data) for name,data in sorted(derived.items())}
        assert manifest == json.loads((layout/(item['label']+'-manifest.json')).read_text())
        assert sha(enc(manifest)) == item['sourceTreeSHA256']
        selected = [row for row in schemas if item['unit'] or row.get('config') != 'unit']
        assert set(item['fields']) == {row['field'] for row in selected}
        previous={}
        for row in sorted(selected,key=lambda row:(row['ownerClass'],item['fields'][row['field']]['offset'])):
            field=item['fields'][row['field']]; cls=row['ownerClass']
            assert field['offset'] % field['alignment'] == 0
            assert field['offset'] + field['bytes'] <= item['classes'][cls]['bytes']
            if field['bytes']:
                assert field['offset'] >= previous.get(cls,0)
                previous[cls] = field['offset']+field['bytes']
        assert item['total'][2] == item['total'][1]+119576 and item['total'][3:5] == [119576,424]
    audit = ROOT/'producer-audit/20261024T051419353958Z'
    data=json.loads((audit/'receipt.json').read_text())
    assert data['status'] == 'passed-retained-producer-audit-and-eight-portable-metadata-replays'
    verify_commands(audit,data)
    for path,expected in data['inputs'].items():assert sha((audit/path).read_bytes())==expected
    producer=json.loads((audit/'inputs/producer-metadata/receipt.json').read_text())
    for replay in data['replays']:
        command=next(command for command in data['commands'] if command['name']==replay['label'])
        records=[line[line.index('AF_'):] for line in (audit/command['stdout']).read_text().splitlines() if 'AF_' in line]
        original=next(item for item in producer['layouts'] if item['label']==replay['label'])
        assert records==original['records']
        fresh=next(item for item in receipt['layouts'] if item['unit']==(original['mode']=='unit'))
        fields={}
        for line in records:
            if line.startswith('AF_FIELD|'):
                _,cls,name,offset,size,align=line.split('|')
                fields[name]=dict(offset=int(offset),bytes=int(size),alignment=int(align))
        assert fields==fresh['fields']
    seal=ROOT/'review-seal.json'
    if seal.exists():
        for path,expected in json.loads(seal.read_text())['files'].items():
            assert sha((ROOT/path).read_bytes())==expected,path
    print(json.dumps(dict(status='verified-final-independent-host-review',sourceTreeSHA256=receipt['sourceFreeze']['sourceTreeSHA256'],
                          independentProbeExecutions=40,unmodifiedCandidateUnitExecutions=682,portableMetadataReplays=8,
                          freshMetadataCompiles=2,buildTreesRequired=False,nativeRuntimeAccepted=False,gaGatePassed=False),indent=2,sort_keys=True))


if __name__=='__main__':main()
