#!/usr/bin/env python3
"""Guarded read-only packet checks; no workflow installation or runtime."""
import unittest.mock
import offline
offline.install()
import argparse, ast, difflib, hashlib, json, os, re, signal, socket, sys
from pathlib import Path
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = HERE.parent / 'swift-pin-bitmap-match-host-admission'
PARSER = HERE.parent / 'swift-pin-bitmap-terminal-parser-correction'
REVIEW = HERE.parent / 'swift-pin-bitmap-match-actual-review'
SOURCE = HERE.parent / 'swift-pin-bitmap-match-binding-correction'
RUNTIME_NAMES = {'host-controls-result.json', 'controls-result.json', 'parser-controls-result.json'}


def row(path):
    raw = b.regular(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def tree(rows):
    return hashlib.sha256(''.join(n + '\0' + rows[n]['sha256'] + '\n' for n in sorted(rows)).encode()).hexdigest()


def packet(path, expected):
    assert row(path/'seal.json')['sha256'] == expected, 'Frozen seal changed: '+path.name
    seal = b.json_data((path/'seal.json').read_bytes())
    for name, expected_row in seal['files'].items():
        assert row(path/b.member(name)) == expected_row, 'Frozen member changed: '+name
    assert tree(seal['files']) == seal['treeSHA256']
    return seal


def functions(text):
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}


def check(*, verify_seal=True, installed_workflow=False):
    for call in (b.subprocess.Popen, os.waitpid, os.setsid, os.killpg, signal.setitimer, socket.socket, b.resource.getrusage):
        assert call is offline.denied
    assert sys.dont_write_bytecode and offline.HERE == HERE
    base = packet(BASE, 'f0af4941e93559c9e26430d19f4dbe7f4e5cd92afc975e44838f7c308c772388')
    actual = packet(REVIEW, '935214e22b97e97473d32826923bebcbf68181c3166f8d55b70ec85458357552')
    source = packet(SOURCE, '0210ab9c252c6f7a5a3eff077e36c2811c79351d916d78b75b2cda88e2bdf85c')
    basis = b.json_data((HERE/'source-basis.json').read_bytes())
    parser = packet(PARSER, basis['parser']['sealSHA256'])
    assert basis['parentSuppliedRevision'] == '1eec8e0fc270c0409c8920ee22fd2374f3bd249f'
    assert basis['parentSuppliedGitTree'] == 'f20be7de5a047f1983931961cc3d774e56de80a3'
    assert basis['GitVerified'] is False
    assert basis['parser']['function'] == row(PARSER/'parser_function.py')
    old, new = (BASE/'admit.py').read_text(), (HERE/'admit.py').read_text()
    before, after = functions(old), functions(new)
    assert set(after)-set(before) == {'prior_evidence'} and set(before)-set(after) == set()
    changed = sorted(n for n in before if before[n] != after[n])
    assert changed == ['checked_command','command_plan','execute','hosted','main','test_evidence']
    assert after['test_evidence'] == (PARSER/'parser_function.py').read_text().rstrip()
    old_nodes, new_nodes = ast.parse(old).body, ast.parse(new).body
    old_nonfunc = [n for n in old_nodes if not isinstance(n, ast.FunctionDef)]
    new_nonfunc = [n for n in new_nodes if not isinstance(n, ast.FunctionDef)]
    def assignment(node):
        return tuple(t.id if isinstance(t, ast.Name) else ast.unparse(t) for t in node.targets) if isinstance(node,ast.Assign) else None
    allowed = {('PROFILE',),('WORKFLOW_PATH',),('(ACTIVE_SECONDS, CLEANUP_SECONDS)',),('PRIOR_EVIDENCE',)}
    assert [ast.dump(n,include_attributes=False) for n in old_nonfunc if assignment(n) not in allowed] == [ast.dump(n,include_attributes=False) for n in new_nonfunc if assignment(n) not in allowed]
    assert a.PROFILE == 'pin-bitmap-release-completion-v1'
    assert a.WORKFLOW_PATH == '.github/workflows/swift-pin-bitmap-release-completion-admission.yml'
    assert (a.ACTIVE_SECONDS,a.CLEANUP_SECONDS,b.MAX_COMMANDS,b.OUTPUT_CAP,b.AGGREGATE_OUTPUT_CAP) == (660,60,6,8388608,33554432)
    for name in ('bounded_commands.py','offline.py','reuse.json'):
        assert (HERE/name).read_bytes() == (BASE/name).read_bytes()
    assert row(HERE/'bounded_commands.py')['sha256'] == '93cc3c4ae578a3f5bf01c09cd143859c48ee3e7b473f9c8f34ead1f60724bee9'
    manifest,data = a.inputs()
    assert len(data) == 136 and len(a.OVERLAYS) == 15
    assert a.CANDIDATE == 'e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1'
    assert a.BASELINE == 'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b'
    assert a.closure(manifest['candidateFiles']) == a.CANDIDATE
    prior = a.prior_evidence()
    assert prior['Debug']['hostParserAdmitted'] is False and prior['Release']['observedPasses'] is None
    assert prior['historicalResultsAreNewRuns'] is False and prior['oldAllowanceConsumed'] is True
    reviewed = b.json_data((REVIEW/'sanitized-result.json').read_bytes())
    assert reviewed['run']['id'] == prior['runID'] and reviewed['run']['attempt'] == prior['attempt']
    assert reviewed['run']['head'] == prior['head'] and reviewed['run']['tree'] == prior['tree']
    assert reviewed['run']['conclusion'] == 'failure'
    assert reviewed['artifact']['id'] == prior['artifactID'] and reviewed['artifact']['sha256'] == prior['artifactSHA256']
    assert reviewed['source']['originalClosure'] == reviewed['source']['formattedClosure'] == prior['sourceClosure'] == a.CANDIDATE
    assert reviewed['source']['diff']['bytes'] == prior['formatter']['changedBytes'] == 0
    assert reviewed['clippy']['exit'] == prior['clippy']['exit'] == 0
    assert reviewed['clippy']['diagnostics'] == prior['clippy']['diagnostics'] == []
    assert reviewed['clippy']['buildFinished'] is prior['clippy']['buildFinished'] is True
    assert reviewed['clippy']['records'] == prior['clippy']['compilerArtifacts'] + 1 == 39
    debug = reviewed['tests']['debug-regression']
    assert debug['admitted'] is prior['Debug']['hostParserAdmitted'] is False
    assert debug['commandExit'] == prior['Debug']['exit'] == 0
    assert debug['summaryPassed'] == debug['independentlyReconstructedTerminals'] == prior['Debug']['passed'] == 699
    assert debug['groupCount'] == prior['Debug']['groups'] == 37
    assert debug['oracleCounts'] == prior['Debug']['nodeOracleCounts']
    assert reviewed['tests']['release-regression']['observedPasses'] is None
    paths = {n:Path('$SCRATCH')/n for n in ('source','target','cargo','home','nodebin')}
    tools = Path('$TOOLBIN')
    plan = a.command_plan(paths,tools,Path('$CONFIG'),{'path':'$NODE'})
    assert [r['name'] for r in plan] == ['compiler-identity','node-identity','release-regression']
    assert [r['seconds'] for r in plan] == [30,30,600]
    assert plan[2]['argv'] == [str(tools/'cargo'),'test','--manifest-path',str(paths['source']/'Cargo.toml'),'--locked','--offline','--all-features','--release','--','--include-ignored','--test-threads=1','--show-output']
    assert all(r['accepted_exits'] == (0,) for r in plan)
    assert 'format_evidence(' not in after['checked_command'] and 'lint_evidence(' not in after['checked_command']
    assert "receipt['DebugPassed']" not in after['execute'] and "receipt['ReleasePassed'] = 699" in after['execute']
    workflow = (HERE/'workflow.yml').read_text()
    assert workflow.startswith('name: Bitmap Release-only completion admission\non:\n  workflow_dispatch:\n')
    assert re.findall(r'^    timeout-minutes: (\d+)$',workflow,re.M) == ['22']
    assert re.findall(r'^        timeout-minutes: (\d+)$',workflow,re.M) == ['2','2','14','1']
    assert workflow.count('rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy') == 1
    assert 'cancel-in-progress: false' in workflow and 'setup-node' not in workflow and 'npm ' not in workflow
    assert 'MIXER_PIN_BITMAP_RELEASE_SELECTION: ${{ inputs.profile }}' in workflow
    assert re.findall(r'^        run: (.+)$',workflow,re.M) == ['|','rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy','python3 -B verification/swift-pin-bitmap-release-completion-admission/admit.py run']
    assert re.findall(r'^          (python3 -B .+)$',workflow,re.M) == ['python3 -B verification/swift-pin-bitmap-release-completion-admission/host_controls.py','python3 -B verification/swift-pin-bitmap-release-completion-admission/controls.py']
    for name in ('admit.py','host_controls.py','workflow.yml'):
        expected_diff = ''.join(difflib.unified_diff((BASE/name).read_text().splitlines(keepends=True),(HERE/name).read_text().splitlines(keepends=True),fromfile='accepted/'+name,tofile='release-only/'+name))
        assert (HERE/(name+'.diff')).read_text() == expected_diff
    if installed_workflow:
        assert row(ROOT/a.WORKFLOW_PATH) == row(HERE/'workflow.yml')
    if verify_seal:
        own = b.json_data((HERE/'seal.json').read_bytes())
        for name,expected in own['files'].items():
            assert row(HERE/b.member(name)) == expected, 'Static member changed: '+name
        assert tree(own['files']) == own['treeSHA256']
        members = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name not in RUNTIME_NAMES and p.name!='seal.json' and not p.relative_to(HERE).is_relative_to('local')}
        assert members == set(own['files'])
    assert not list(HERE.glob('pure-*')) and not list(HERE.rglob('__pycache__'))
    assert offline.ATTEMPTS == []
    return {'schema':1,'sourceOnly':True,'candidateMembers':136,'overlays':15,'candidateTreeSHA256':a.CANDIDATE,'parserFunction':row(PARSER/'parser_function.py'),'changedExistingFunctions':changed,'addedFunctions':['prior_evidence'],'helperByteIdentical':True,'commands':[r['name'] for r in plan],'activeSeconds':660,'cleanupSeconds':60,'workflowSHA256':row(HERE/'workflow.yml')['sha256'],'priorReviewSealSHA256':prior['reviewSealSHA256'],'installedWorkflowChecked':installed_workflow,'staticSealChecked':verify_seal,'runtimeRuns':0,'liveApiAttempts':offline.ATTEMPTS,'validationScope':'Guarded source, hashes, exact AST change set and structural workflow checks; no YAML/actionlint or runtime validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-workflow',action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(installed_workflow=args.installed_workflow),sort_keys=True))
