#!/usr/bin/env python3
"""Freeze source-specific obligations from released packets, never execute them."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEMANTIC = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1'
INPUTS = {
    SEMANTIC: '361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6',
    ROOT / 'verification/android-renderer-finite-membership-controls': 'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93',
    ROOT / 'verification/android-source-pair5-coherent-integration-preparation': '0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b',
}
PREFIX = 'dev/mixer/android/NativeEditorConnectionV2'
CLASSES = {PREFIX: 2, PREFIX+'$Base': 70, PREFIX+'$Api31': 8, PREFIX+'$Api33': 16, PREFIX+'$Api34': 7}
STATES = ['clean', 'terminal-at-entry', 'terminal-before-return', 'dirty-at-entry', 'dirty-before-return', 'ordinary-throw-after-callback', 'fatal-throw-after-callback']
UNSUPPORTED = {'sendKeyEvent', 'commitContent', 'commitCorrection', 'performPrivateCommand', 'performSpellCheck', 'replaceText', 'previewHandwritingGesture'}
# These are independently read branches in the exact sealed 81-line source, not
# inferred callback coverage or a runtime eligibility decision.
GUARDS = {
    32: 'proposal(text,false)', 33: 'proposal(text,true)',
    34: 'start>=0 && end>=0 && start<=editable.length && end<=editable.length',
    36: 'before>=0 && after>=0', 37: 'before>=0 && after>=0',
    38: 'start>=0 && end>=0 && start<=editable.length && end<=editable.length',
    39: 'completion!=null && proposal(completion.getText(),false)',
    41: 'action==EditorInfo.IME_ACTION_DONE', 47: 'mode==0', 48: 'flags==0',
    50: 'length>=0', 51: 'length>=0', 58: 'before>=0 && after>=0',
    64: 'proposal(text,false)', 65: 'proposal(text,true)',
    66: 'start>=0 && end>=0 && start<=editable.length && end<=editable.length',
    67: 'mode==0 && filter==0',
}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_member(base, name):
    seal = json.loads((base/'seal.json').read_text())
    entry = next(x for x in seal['members'] if x['path'] == name)
    path = base/name
    assert sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'], name
    return path

def tuple_for(s, i):
    return {k: s[k] for k in ('class', 'method', 'descriptor', 'source_sha256', 'class_sha256')} | {
        'bci': i['bci'], 'opcode': i['opcode'], 'mnemonic': i['mnemonic'], 'callee': i['target']}

def build():
    for base, expected in INPUTS.items():
        assert sha(base/'seal.json') == expected
    roster = json.loads(read_member(SEMANTIC, 'active-semantic-obligations.json').read_text())
    history = json.loads(read_member(SEMANTIC, 'historical189-current-bindings.json').read_text())
    context = json.loads(read_member(SEMANTIC, 'product-context.json').read_text())
    source = read_member(SEMANTIC, 'accepted-source/NativeEditorConnectionV2.java')
    lines = source.read_text().splitlines()
    assert len(lines) == 81
    selected = [s for s in roster['subjects'] if s['class'] in CLASSES]
    assert dict(Counter(s['class'] for s in selected)) == CLASSES
    assert len({s['id'] for s in roster['subjects']}) == 280
    assert len(context['source_map']) == 16 and len(context['class_map']) == 209
    # Cross-packet identities include the selected run only, never another run.
    for name, expected in context['source_map'].items():
        p = read_member(list(INPUTS)[1], 'inputs/product/'+name)
        assert sha(p) == expected['sha256']
    for name, expected in context['class_map'].items():
        p = read_member(list(INPUTS)[1], 'run-3/classes/'+name)
        assert sha(p) == expected['sha256']
    overlay = read_member(list(INPUTS)[2], 'source/native/android/app/src/dev/mixer/android/NativeEditorConnectionV2.java')
    assert sha(overlay) == sha(source)
    policies = []
    for s in selected:
        calls = s['invocations']
        native = [i for i in calls if i['target']['owner'] == 'android/view/inputmethod/InputConnection']
        line = s['returns_and_throws'][0]['line']
        # Public callback closing braces report the following line in bytecode.
        if s['method'] == 'performHandwritingGesture': line = 75
        if s['method'] == 'requestTextBoundsInfo': line = 78
        if s['method'] == '<init>': role = 'constructor'
        elif s['method'] == 'create': role = 'factory'
        elif s['method'] == 'getHandler': role = 'pure-any-thread-null'
        elif s['method'] in UNSUPPORTED or s['method'] == 'no': role = 'main-thread-constant-false'
        elif s['method'] in ('call', 'nativeValue'): role = 'field-helper-delegation'
        elif s['method'] == 'closeConnection': role = 'field-close-delegation'
        elif s['method'] in ('performHandwritingGesture', 'requestTextBoundsInfo'): role = 'unsupported-executor-callback'
        elif s['method'].startswith('lambda$'):
            if native: role = 'inner-native-supplier'
            elif any(i['target']['owner'] in ('java/util/function/Consumer', 'java/util/function/IntConsumer') for i in calls): role = 'unsupported-callback-body'
            elif any(i['target']['name'] == 'proposal' for i in calls): role = 'proposal-guard-supplier'
            elif any(i['target']['owner'] == 'android/text/Editable' for i in calls): role = 'bounds-guard-supplier'
            else: role = 'outer-native-value-supplier'
        else: role = 'public-adapter'
        native_siblings = [q for q in selected if q['class'] == s['class'] and any(i.get('line') == line and i['target']['owner'] == 'android/view/inputmethod/InputConnection' for i in q['invocations'])]
        public_siblings = [q for q in selected if q['class'] == s['class'] and not q['method'].startswith('lambda$') and q['method'] not in ('<init>', 'create', 'call', 'nativeValue', 'no') and any(r.get('line') == line for r in q['returns_and_throws'])]
        if role == 'public-adapter': public_siblings = [s]
        original_return = (public_siblings[0]['descriptor'] if public_siblings else s['descriptor']).split(')')[1]
        result_type = 'boolean' if original_return in ('Z', 'Ljava/lang/Boolean;') else 'int' if original_return in ('I', 'Ljava/lang/Integer;') else 'void' if original_return == 'V' else 'reference'
        refused = {'kind': 'boolean', 'value': False} if result_type == 'boolean' else {'kind': 'int', 'value': 0} if result_type == 'int' else {'kind': 'void'} if result_type == 'void' else {'kind': 'null'}
        pending_role = role in ('constructor', 'factory', 'field-helper-delegation', 'field-close-delegation')
        case_policies = []
        for case in s['required_semantic_cases']:
            state = 'clean'
            rule = 'pending-helper-or-enclosing-specific-outcome'
            if case == 'current-exact-original-result': rule = 'exact-clean-result'
            elif case == 'wrong-thread-refuses': rule = 'any-thread-null' if role == 'pure-any-thread-null' else 'main-thread-refusal'
            elif case == 'unsupported-argument-refuses' and (line in GUARDS or role == 'main-thread-constant-false'): rule = 'guard-refusal'
            elif case in ('terminal-before-entry-refuses', 'dirty-before-entry-refuses'):
                state = 'terminal-at-entry' if case.startswith('terminal') else 'dirty-at-entry'
                rule = 'entry-refusal'
            elif case in ('stale-before-entry-refuses', 'changing-before-entry-refuses'): rule = 'entry-refusal'
            elif case == 'ordinary-after-callback-exact-identity': state, rule = 'ordinary-throw-after-callback', 'exact-original-exception'
            elif case in ('fatal-after-callback-first-fatal', 'first-fatal-exact-identity'): state, rule = 'fatal-throw-after-callback', 'exact-first-fatal'
            if role == 'inner-native-supplier' and rule == 'guard-refusal': rule = 'pending-guard-is-outside-inner-supplier'
            if pending_role: rule = 'pending-helper-or-enclosing-specific-outcome'
            if role in ('pure-any-thread-null', 'main-thread-constant-false') and rule in ('exact-original-exception', 'exact-first-fatal'):
                rule = 'pending-no-native-callback-in-this-body'
            case_policies.append({'case_id': case, 'state_id': state, 'rule': rule, 'state_phase': 'public-adapter-entry' if rule == 'entry-refusal' else 'case-specific', 'disposition': 'pending-fresh-typed-outcome', 'original_case_retained': True})
        state_rules = []
        for state in STATES:
            rule = 'pending-helper-or-enclosing-specific-outcome' if pending_role else 'exact-clean-result' if state == 'clean' else 'postcheck-refused-public-result' if state.endswith(('before-return', 'at-entry')) else 'exact-original-exception' if state.startswith('ordinary') else 'exact-first-fatal'
            if role in ('pure-any-thread-null', 'main-thread-constant-false') and state != 'clean': rule = 'pending-no-native-callback-in-this-body'
            if role.startswith('unsupported-'): rule = 'unsupported-callback-result-and-executor-identity' if state == 'clean' else 'pending-executor-callback-specific-observation'
            state_rules.append({'state_id': state, 'state_phase': 'native-hook-entry' if state.endswith('at-entry') else 'native-hook-before-return' if state.endswith('before-return') else 'case-specific', 'rule': rule, 'disposition': 'pending-fresh-typed-outcome'})
        policy = {k: s[k] for k in ('id', 'class', 'method', 'descriptor', 'source_sha256', 'class_sha256', 'categories', 'required_semantic_cases')}
        policy.update(role=role, source_line=line, source_line_text=lines[line-1], oracle_source_sha256=sha(source),
            oracle={'id': s['id']+'@source-specific-v1', 'kind': 'source-derived-result-constraint-only', 'actual_outcomes_required': True,
                'callback_contract': 'main-thread; nonnull executor and consumer schedule exactly unsupported result; null executor or consumer schedules none; executor or consumer exceptions require exact actual observations' if role.startswith('unsupported-') else None,
                'constructor_factory_contract': 'Base captures field/attempt and attempt.target; subclasses delegate exact superclass constructor; factory SDK>=34 Api34, >=33 Api33, >=31 Api31, else Base; no lifecycle callback is fabricated' if pending_role and role in ('constructor', 'factory') else None},
            source_guard=GUARDS.get(line), result_type=result_type, refused_result=refused,
            exact_invocations=[tuple_for(s, i) for i in calls], returns_and_throws=s['returns_and_throws'],
            native_supplier_ids=[q['id'] for q in native_siblings], public_adapter_ids=[q['id'] for q in public_siblings],
            case_policies=case_policies, required_states=state_rules,
            state_aliases={'current': 'clean'}, qualification='pending; source mapping is not runtime outcome evidence')
        policies.append(policy)
    replacements = []
    for record in history['records']:
        if record['disposition'] == 'replaced-direct-adapter' and any(c['class'] in CLASSES for c in record['fresh_compiled_candidates']):
            assert len(record['fresh_compiled_candidates']) == 1
            candidate = record['fresh_compiled_candidates'][0]
            subject_id = candidate['class']+'#'+candidate['method']+candidate['descriptor']
            subject = next(s for s in policies if s['id'] == subject_id)
            invocation = next(i for i in subject['exact_invocations'] if i['bci'] == candidate['bci'])
            assert invocation['callee'] == candidate['target']
            replacements.append({'historical_id': record['historical_id'], 'disposition': record['disposition'], 'subject_id': subject_id, 'invocation': invocation, 'behavioral_state_qualification': 'pending'})
    assert len(replacements) == 9 and len(history['records']) == 189
    result = {'schema': 'mixer-editor-subject-policy-v1', 'context_id': context['context_id'],
        'input_seals': {str(p.relative_to(ROOT)): v for p,v in INPUTS.items()},
        'source_map_sha256': hashlib.sha256(canonical(context['source_map'])).hexdigest(),
        'class_map_sha256': hashlib.sha256(canonical(context['class_map'])).hexdigest(),
        'execution_closure_sha256': None, 'execution_closure_status': 'pending-fresh-execution-source-closure',
        'source_count': 16, 'product_class_count': 209, 'semantic_subject_count': 280,
        'editor_subject_count': 103, 'class_counts': CLASSES, 'canonical_states': STATES,
        'historical189_binding_sha256': sha(SEMANTIC/'historical189-current-bindings.json'),
        'historical189_ids': [r['historical_id'] for r in history['records']], 'historical9_replacements': replacements,
        'out_of_scope_replacement_links': [{'historical_id': r['historical_id'], 'disposition': r['disposition'], 'compiled_candidates': [{k: c[k] for k in ('class','method','descriptor','bci','target','source_sha256','class_sha256')} for c in r['fresh_compiled_candidates']], 'owner': 'NativeField policy lane; no qualification inherited here'} for r in history['records'] if r['disposition'] == 'replaced-direct-adapter' and not any(c['class'] in CLASSES for c in r['fresh_compiled_candidates'])],
        'subjects': policies, 'acceptance_scope': 'typed row joins only; full matrix, closure, native, OTA and GA pending'}
    (HERE/'policy.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'subjects': 103, 'replacements': 9, 'policy_sha256': sha(HERE/'policy.json')}))

if __name__ == '__main__': build()
