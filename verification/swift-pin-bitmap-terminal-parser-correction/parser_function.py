def test_evidence(text):
    # libtest writes ordinary terminals on one line, but direct stdout writes
    # can separate a serialized test header from its standalone terminal. Bind
    # both forms to running groups; captured --show-output text is never a test.
    need(type(text) is str and len(text.encode('utf-8')) <= 8*1024*1024, 'Test evidence text bound')
    need(not re.search(r'[\x00-\x08\x0b-\x1f\x7f]', text), 'Control characters in test evidence')
    summary_pattern = r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;(?: finished in \d+(?:\.\d+)?s)?'
    split_names = {
        'shared_control_branch_targets_and_frame_boundary',
        'shared_control_cancellation_and_limits',
        'shared_control_close_partial_effects',
        'shared_control_public_parity_trace',
        'shared_control_warm_dispatch_allocation_free',
        'shared_control_work_and_fuel_prefixes',
    }
    allocation = r'\(\d+, \d+, \d+\)'
    usage = r'ExecutionUsage \{ [^{}\n]* \}'
    cache = r'CacheUsage \{ [^{}\n]* \}'
    config = r'Limits \{ [^{}\n]* \}/ExecutionBudget \{ [^{}\n]* \}/CacheBudget \{ [^{}\n]* \}/(?:true|false)/\d+/\d+'
    trace_pattern = r'control_trace [a-z][a-z0-9-]* config=' + config + r' (?:constructor=[^\n]+ allocations=' + allocation + r'|initial=' + usage + r' first=[^\n]+ final=' + usage + r' cache=' + cache + r' allocations=' + allocation + '/' + allocation + ')'
    warm_pattern = r'control_warm [a-z][a-z0-9-]* usage=' + usage + r' cache=' + cache + r' allocations=' + allocation
    ceiling_pattern = r'control_validation_ceiling (operand|control) failure=Failure \{ kind: ResourceExhausted, code: "profile_\1_limit", [^\n]+ \}'
    identifier = r'[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*'
    doctest = r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.rs - ' + identifier + r' \(line [1-9]\d*\)(?: - compile fail)?'
    rows, terminals, names = [], [], set()
    group = None
    pending = None
    traces = 0
    for line in text.split('\n'):
        stripped = line.lstrip()
        if stripped.startswith('running '):
            match = re.fullmatch(r'running (0|[1-9]\d*) (test|tests)', line)
            need(match is not None and group is None and pending is None, 'Malformed or overlapping running group')
            count = int(match[1])
            need(count <= 699 and match[2] == ('test' if count == 1 else 'tests') and len(rows) < 700, 'Running group count or grammar')
            group = {'running': count, 'terminals': 0, 'output': False}
        elif stripped.startswith('test result'):
            match = re.fullmatch(summary_pattern, line)
            need(match is not None and group is not None and pending is None, 'Malformed, orphan or unfinished test summary')
            need(match[1] == 'ok', 'Non-ok test summary')
            row = dict(zip(('passed', 'failed', 'ignored', 'measured', 'filtered'), map(int, match.groups()[1:])))
            need(all(row[k] == 0 for k in ('failed', 'ignored', 'measured', 'filtered')), 'No failed, ignored, measured or filtered tests')
            need(group['running'] == group['terminals'] == row['passed'], 'Running, terminal and summary counts disagree')
            rows.append(row)
            group = None
        elif stripped.startswith('test ') and (group is None or not group['output'] or ' ... ' in line):
            need(group is not None and not group['output'] and pending is None, 'Orphan, captured or overlapping test header')
            need(line.startswith('test ') and line.count(' ... ') == 1, 'Malformed test header')
            name, status = line[5:].split(' ... ', 1)
            need(re.fullmatch(identifier, name) or re.fullmatch(doctest, name), 'Malformed test identity')
            need(name not in names, 'Duplicate test identity')
            need(group['terminals'] < group['running'] and len(terminals) < 699, 'Too many test headers')
            names.add(name)
            if status == 'control_observer serialized lane':
                need(name in split_names, 'Unrecognized split test identity')
                pending, traces = name, 0
            else:
                need(status == 'ok', 'Non-ok or malformed terminal test status')
                terminals.append((name, status))
                group['terminals'] += 1
        elif pending is not None:
            if line == 'ok':
                need(traces > 0, 'Split terminal requires serialized trace output')
                terminals.append((pending, 'ok'))
                group['terminals'] += 1
                pending = None
            else:
                trace = re.fullmatch(trace_pattern, line)
                warm = pending == 'shared_control_warm_dispatch_allocation_free' and re.fullmatch(warm_pattern, line)
                ceiling = pending == 'shared_control_cancellation_and_limits' and re.fullmatch(ceiling_pattern, line)
                need(trace is not None or warm or ceiling, 'Malformed split trace or terminal transition')
                traces += int(trace is not None)
        elif stripped.startswith(('control_trace', 'control_warm', 'control_observer', 'control_validation_ceiling')):
            need(False, 'Orphan serialized control output')
        elif stripped == 'ok' or stripped.startswith(('FAILED', 'ignored')):
            need(False, 'Orphan or non-ok standalone test result')
        elif stripped == 'successes:':
            need(line == stripped and group is not None and group['terminals'] == group['running'], 'Premature or orphan captured output')
            group['output'] = True
        else:
            need(not line or (group is not None and group['output']), 'Unexpected output outside captured test output')
    need(group is None and pending is None and rows, 'Missing summary or unfinished running group')
    need(sum(r['passed'] for r in rows) == 699, 'Exactly 699 passed tests required')
    need(len(terminals) == 699, 'Exactly 699 terminal ok lines required')
    oracle_names = collections.Counter(name for name, _ in terminals)
    need(all(oracle_names[n] == 1 for n in ORACLES), 'All nine exact Node oracles must pass once')
    return {'summaries': rows, 'terminals': terminals, 'passed': 699, 'ignored': 0, 'nodeOracles': list(ORACLES),
            'scope': 'Full all-feature host Debug or Release, including explicit development Node oracles; no production Node interpreter'}
