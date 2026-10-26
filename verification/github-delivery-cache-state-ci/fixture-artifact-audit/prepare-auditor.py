"""Adapt the accepted raw-content auditor to a read-only in-memory ZIP view."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]
previous=REPO/'verification/swift-cache-state-ci-independent/corrected-review/audit_full.py'
code=previous.read_text()
original_hash=hashlib.sha256(previous.read_bytes()).hexdigest()
code=code.replace('import gzip\n','import ast\nimport gzip\nimport stat\nimport types\nimport zipfile\n')
code=code.replace("RUN = HERE / 'correction-2-copy/runs/independent-rust-1-99-full'", """CANONICAL = HERE / 'sources/verification/swift-cache-state-ci'
RUN_PREFIX = 'runs/ci-40373807988-1'
DATA = {}
class ArchivePath:
    def __init__(self,path=''): self.path = str(path).strip('/')
    def __truediv__(self,other): return ArchivePath(self.path + '/' + str(other))
    def read_bytes(self): return DATA[self.path]
    def read_text(self): return self.read_bytes().decode()
    def stat(self): return types.SimpleNamespace(st_size=len(self.read_bytes()))
    def exists(self): return self.path in DATA or any(p.startswith(self.path + '/') for p in DATA)
    def __str__(self): return self.path
RUN = ArchivePath(RUN_PREFIX)""")
code=code.replace("EXPECTED_REVISION = '8ac624160a2cfff10d201d8063f69cf05f005edb'", "EXPECTED_REVISION = 'db6332d4c27efec4f9e22b9adc43000d48c591a1'\nEXPECTED_TREE = 'dc76d1caa4ad6db89b51f82172314dd6d4b89995'")
old="""    launch = strict((HERE / 'evidence/full-invocation/launch.json').read_bytes())
"""
assert old in code;code=code.replace(old,'')
code=code.replace("    receipt = strict((RUN / 'receipt.json').read_bytes())", "    archive_summary, controls = validate_archive()\n    receipt = strict((RUN / 'receipt.json').read_bytes())")
old="    assert launch['exit'] == 0 and launch['child_returned'] and launch['foreign_directory_unchanged']"
assert old in code;code=code.replace(old,"    assert receipt['source_tree'] == EXPECTED_TREE")
code=code.replace("assert receipt['rustc']['identity']['release'] == '1.99.0'", "assert receipt['rustc']['identity']['release'] in ('1.98.1', '1.99.0')")
old="    assert api['probes'] == strict((HERE.parent / 'independent-api-contract.json').read_bytes())['probes']\n    own = strict((HERE.parent / 'independent-expected-inventory.json').read_bytes())\n    assert layouts['layouts'] == own['complete_producer_layouts']"
new="    assert api == strict((CANONICAL / 'pack/inventories/api-contract.json').read_bytes())\n    assert layouts == strict((CANONICAL / 'pack/inventories/layouts.json').read_bytes())"
assert old in code;code=code.replace(old,new)
code=code.replace("    scratch = RUN / 'scratch'", "    scratch = Path(receipt['commands'][0]['cwd']) / 'scratch'")
code=code.replace("        assert row['child_returned'] and row['owned_group_gone']", "        assert row['per_child_limit_seconds'] == 60 and row['per_stream_cap_bytes'] == 8 * 1024 * 1024\n        assert row['child_returned'] and row['owned_group_gone']")
old="'launch_receipt_sha256': sha(HERE / 'evidence/full-invocation/launch.json'),"
new="'artifact_sha256': archive_summary['sha256'], 'artifact': archive_summary, 'focused_controls': controls,"
assert old in code;code=code.replace(old,new)
code=code.replace("'all103children_owned_TMP': True, 'hostile_inherited_directory_unchanged': True,", "'all103children_owned_TMP': True, 'normal_full_invocations': 1,")
old="""'passed': True, 'limits': ['Actual Rust1.99.0 macOS arm64 host fixture closure only',
            'Historical full producer Debug60s timeout remains failed; no performance equivalence',
            'No Rust1.98.1, canonical CI/runtime, general public File, native, signing/store, FieldLog, operations or GA qualification']}"""
new="""'passed': True, 'limits': [
            'Actual recorded selected compiler and dedicated Actions host fixture closure only; no local reexecution',
            'Compiler, launcher and Python executable bytes are absent; their hashes and postflight identity checks are receipt claims bound to retained version/command output',
            'Fourteen compiler products were hashed before removal per receipt; binary bytes are absent and were not executed by this audit',
            'Scratch/process-group/temporary-directory cleanup is retained receipt evidence; no remote filesystem or process inspection was performed',
            'Historical full producer Debug60s timeout remains failed; no performance equivalence',
            'Overall workflow was still running when the new fixture job completed; no global CI success claim',
            'No general public File admission, canonical runtime, target/native, signing/store, immutable package FieldLog, customer operations or GA qualification']}"""
assert old in code;code=code.replace(old,new)
code=code.replace("    (HERE / 'full-audit.json').write_text", "    validate_postflight(receipt, retention, mode_results)\n    report['actual_compiler_release'] = receipt['rustc']['identity']['release']\n    report['retained_logical_bytes_verified'] = sum(r['bytes'] for r in retention['files'])\n    report['unique_content_members_verified'] = len({r['content'] for r in retention['files']})\n    (HERE / 'full-audit.json').write_text")
(ROOT/'audit-content.py').write_text(code)
(ROOT/'adaptation.json').write_text(json.dumps({'source':str(previous.relative_to(REPO)),'source_sha256':original_hash,'to':'audit-content.py','changes':['Fresh exact CI commit/tree constants','In-memory archive paths instead of local run paths; no archive extraction or execution','Canonical exact git-show pack bindings replace prior local inventory paths','Actual selected compiler release is derived from retained receipt and raw identity output','Focused controls, full archive custody, source/derivative, raw postflight and failure-evidence verification added','Local hostile-environment launch claim removed; CI actual scope and hash-only limitations explicit'],'scope':'Auditor source copied and adapted; old one-shot script not executed'},indent=2)+'\n')
