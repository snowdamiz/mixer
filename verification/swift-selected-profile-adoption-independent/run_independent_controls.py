"""Add private test-only controls in an owned exact-source variant."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CANDIDATE=ROOT/'verification/swift-selected-profile-adoption'
EXTRA=HERE/'independent-controls'


def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')


def prepare():
    assert not EXTRA.exists();EXTRA.mkdir()
    for m in load(CANDIDATE/'source-manifest.json')['members']:
        p=CANDIDATE/'source/vm'/m['path'];b=p.read_bytes()
        assert len(b)==m['bytes'] and sha(b)==m['sha256']
        q=EXTRA/'source/vm'/m['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    shutil.copytree(CANDIDATE/'host',EXTRA/'host')
    for p in (HERE/'replay').iterdir():
        if p.is_file() and p.name in ['evidence.py','selection.json','prepare_inputs.py','implement_selected.py','extend_roster.py','migrate_literals.py','contracts.py','public_contracts.py','CONTRACT-PROPOSAL.md','appended-layout-types.json']:
            shutil.copyfile(p,EXTRA/p.name)
    path=EXTRA/'evidence.py';old=path.read_text();new=old.replace("if ordinary and case=='narrowed':budget=", "if (ordinary and case=='narrowed') or (not ordinary and case=='independent-narrowed'):budget=")
    assert new!=old;path.write_text(new)
    loader=EXTRA/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs'
    old=loader.read_text()
    new=old.replace('if scenario == "narrowed" {','if scenario == "narrowed" || scenario == "adopt-independent-narrowed" {')
    needle='if let Some(case)=scenario.strip_prefix("adopt-") {\n                super::super::cache::test_selected_initial_outcome_v1(selected,case);'
    replacement='if scenario.starts_with("adopt-independent-") {\n                independent_selected_controls(selected,scenario.strip_prefix("adopt-").unwrap());\n            } else if let Some(case)=scenario.strip_prefix("adopt-") {\n                super::super::cache::test_selected_initial_outcome_v1(selected,case);'
    assert needle in new;new=new.replace(needle,replacement)
    new+='\n'+(HERE/'independent_selected_controls.rs').read_text()
    loader.write_text(new)
    control=EXTRA/'source/vm/src/experimental_swift_reactor/control.rs'
    control.write_text(control.read_text()+'\n'+(HERE/'independent_refund_controls.rs').read_text())
    write(HERE/'independent-controls-adaptation.json',{'schema':1,'candidate_source_sha256':'22b6e945a062b3465156bb9995bce610bd712fa9d3e283e176316d75104bb442','modified_paths':['src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs'],'scope':'append test-only private ticket fault checks; route new genuine loader test scenarios; use existing independent exact runtime floor and full typed payload comparisons; narrowed allfivebudget fixture','native_UI_capture_process_inventory':False,'candidate_mutated':False})


def module():
    spec=importlib.util.spec_from_file_location('independent_adoption_control_evidence',EXTRA/'evidence.py')
    e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e);return e


if sys.argv[1]=='prepare':prepare()
else:
    e=module();mode=sys.argv[2]
    if sys.argv[1]=='compile':e.compile(mode)
    elif sys.argv[1]=='run':
        cases=['independent-parity-'+x for x in ['source','metadata','combined','invalid','cancelled','deadline']]
        cases+=['independent-refund-'+x for x in ['source','metadata','both']]
        cases+=['independent-boundary-'+x for x in ['below','equal','above']]
        cases+=['independent-narrowed']
        e.selected(mode,cases)
    else:raise AssertionError(sys.argv[1])
