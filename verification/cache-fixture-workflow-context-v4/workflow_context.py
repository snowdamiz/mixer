"""Restricted data-only YAML/context check, not an official Actions validator.

Accept only the mappings, sequences, scalars and literal blocks used by this
candidate. Reject other YAML constructs. Context allowlists are transcribed
from the cited official documentation/schema in context-rules.json. No shell
or expression is evaluated; this does not replace GitHub's workflow parser.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def need(value, message):
    if not value:
        raise ValueError(message)


def scalar(value):
    need(value and value[0] not in '&*!>|[{', 'Unsupported YAML scalar')
    if value[0] in "\"'":
        need(len(value) >= 2 and value[-1] == value[0], 'Unclosed quote')
        if value[0] == '"':
            return json.loads(value)
        return value[1:-1].replace("''", "'")
    need(' #' not in value and ': ' not in value, 'Ambiguous plain scalar')
    if value in ('true', 'false'):
        return value == 'true'
    if value in ('null', '~'):
        return None
    if value.isdecimal():
        return int(value)
    return value


def parse(source):
    """Parse the explicitly limited YAML subset; preserve `on` as a string."""
    lines = source.splitlines()
    need(not any('\t' in line or '\r' in line for line in lines), 'Tabs/CR forbidden')
    for line in lines:
        need(line.strip() not in ('---', '...'), 'Multiple/document markers unsupported')

    def skip(pos):
        while pos < len(lines) and not lines[pos].strip():
            pos += 1
        return pos

    def indent(pos):
        return len(lines[pos]) - len(lines[pos].lstrip(' '))

    def pair(text, pos, level):
        key, sep, tail = text.partition(':')
        need(sep and key and all(c.isalnum() or c in '_-' for c in key), 'Invalid mapping key')
        need(not tail or tail.startswith(' '), 'Mapping separator required')
        value = tail.strip()
        if value == '|':
            end = pos
            while end < len(lines) and (not lines[end].strip() or indent(end) > level):
                end += 1
            nonblank = [indent(i) for i in range(pos, end) if lines[i].strip()]
            need(nonblank and min(nonblank) == level + 2, 'Literal indentation differs')
            return key, '\n'.join(line[level + 2:] if line.strip() else ''
                                  for line in lines[pos:end]) + '\n', end
        if value:
            return key, scalar(value), pos
        child = skip(pos)
        if child < len(lines) and indent(child) > level:
            need(indent(child) == level + 2, 'Unexpected child indentation')
            value, end = block(child, level + 2)
            return key, value, end
        return key, None, pos

    def mapping(pos, level, first=None):
        result = {}
        if first is not None:
            key, value, pos = pair(first, pos, level)
            result[key] = value
        while (pos := skip(pos)) < len(lines) and indent(pos) >= level:
            need(indent(pos) == level and not lines[pos][level:].startswith('- '),
                 'Unexpected mapping indentation/type')
            key, value, pos = pair(lines[pos][level:], pos + 1, level)
            need(key not in result, 'Duplicate mapping key: ' + key)
            result[key] = value
        return result, pos

    def block(pos, level):
        if not lines[pos][level:].startswith('- '):
            return mapping(pos, level)
        result = []
        while (pos := skip(pos)) < len(lines) and indent(pos) >= level:
            need(indent(pos) == level and lines[pos][level:].startswith('- '),
                 'Unexpected sequence indentation/type')
            text = lines[pos][level + 2:]
            value, pos = mapping(pos + 1, level + 2, text)
            result.append(value)
        return result, pos

    start = skip(0)
    need(start < len(lines) and indent(start) == 0, 'Root must start at column one')
    result, end = block(start, 0)
    need(skip(end) == len(lines), 'Trailing YAML unsupported')
    return result


def expressions(text, allowed, location):
    if not isinstance(text, str):
        return []
    references = []
    offset = 0
    while True:
        start = text.find('${{', offset)
        if start < 0:
            need('}}' not in text[offset:], 'Unmatched expression closer')
            return references
        end = text.find('}}', start + 3)
        need(end >= 0, 'Unclosed expression')
        expression = text[start + 3:end].strip()
        # This candidate uses only simple two-component property references.
        # Fail closed for operators, indexing, calls and unknown syntax.
        parts = expression.split('.')
        need(len(parts) == 2 and all(part and all(c.isalnum() or c == '_' for c in part)
                                     and not part[0].isdigit() for part in parts),
             'Unsupported expression grammar at ' + location)
        need(parts[0] in allowed, 'Context ' + parts[0] + ' unavailable at ' + location)
        references.append({'location': location, 'expression': expression})
        offset = end + 2


def validate(document, rules=None):
    rules = rules or json.loads((HERE / 'context-rules.json').read_text())
    refs = []

    def shape(value, allowed, required, location):
        need(isinstance(value, dict) and set(value) <= set(allowed)
             and set(required) <= set(value), 'Unsupported mapping shape at ' + location)

    def env(value, kind, location):
        need(isinstance(value, dict), 'Environment must be a map')
        for key, item in value.items():
            need(isinstance(item, str), 'Environment must contain strings')
            refs.extend(expressions(item, rules['contexts'][kind], location + '.' + key))

    shape(document, ['name', 'on', 'permissions', 'concurrency', 'jobs', 'env'],
          ['name', 'on', 'permissions', 'concurrency', 'jobs'], 'workflow-root')
    need(isinstance(document['name'], str), 'Workflow name must be a string')
    need(document['on'] == {'workflow_dispatch': None}, 'Only manual dispatch accepted')
    need(document['permissions'] == {'contents': 'read'}, 'Read-only contents permission required')
    shape(document['concurrency'], ['group', 'cancel-in-progress'],
          ['group', 'cancel-in-progress'], 'concurrency')
    need(document['concurrency']['cancel-in-progress'] is False, 'No cancellation of prior invocation')
    refs.extend(expressions(document['concurrency']['group'], rules['contexts']['workflow-concurrency'],
                            'concurrency.group'))
    if 'env' in document:
        env(document['env'], 'workflow-env', 'env')
    need(isinstance(document['jobs'], dict) and len(document['jobs']) == 1, 'One job required')
    for name, job in document['jobs'].items():
        shape(job, ['runs-on', 'timeout-minutes', 'env', 'steps'],
              ['runs-on', 'timeout-minutes', 'env', 'steps'], 'jobs.' + name)
        need(job['runs-on'] == 'macos-15' and type(job['timeout-minutes']) is int
             and job['timeout-minutes'] == 30, 'Runner or job bound differs')
        env(job['env'], 'job-env', 'jobs.' + name + '.env')
        need(isinstance(job['steps'], list) and job['steps'], 'Steps sequence required')
        for index, step in enumerate(job['steps']):
            location = 'jobs.' + name + '.steps.' + str(index)
            shape(step, ['name', 'uses', 'with', 'env', 'if', 'timeout-minutes', 'shell', 'run'],
                  [], location)
            need(('run' in step) != ('uses' in step), 'Exactly one run or uses required')
            if 'run' in step:
                need(step.get('shell') == 'bash' and isinstance(step['run'], str), 'Bash run required')
            else:
                need(isinstance(step['uses'], str), 'Action must be a string')
            if 'timeout-minutes' in step:
                need(type(step['timeout-minutes']) is int and 1 <= step['timeout-minutes'] <= 12,
                     'Step timeout invalid')
            if 'if' in step:
                need(step['if'] == 'always()', 'Only known always() step condition accepted')
            if 'env' in step:
                env(step['env'], 'step-env', location + '.env')
            for key in ['run', 'name', 'uses']:
                if key in step:
                    refs.extend(expressions(step[key], rules['contexts']['steps'], location + '.' + key))
            if 'with' in step:
                need(isinstance(step['with'], dict), 'Action inputs must be a map')
                for key, value in step['with'].items():
                    refs.extend(expressions(value, rules['contexts']['steps'], location + '.with.' + key))
    return {'expression_references': refs, 'scope': 'restricted structural and official context allowlist check',
            'official_validator': False, 'shell_or_workflow_executed': False}


def expected_document(original):
    """Enumerate the only authorized semantic changes to the parsed v3 data."""
    from copy import deepcopy
    result = deepcopy(original)
    result['name'] = 'Cache fixture workflow context v4'
    result['concurrency']['group'] = result['concurrency']['group'].replace(
        'cache-fixture-compiler-admission-v3-', 'cache-fixture-workflow-context-v4-')
    job = result['jobs']['complete-fixture-on-declared-compiler']
    home = job['env'].pop('RUSTUP_HOME')
    steps = job['steps']
    for index in [3, 4]:
        steps[index]['env'] = {'RUSTUP_HOME': home}
    old_name = 'cache-fixture-compiler-admission-v3.yml'
    new_name = 'cache-fixture-workflow-context-v4.yml'
    steps[0]['with']['sparse-checkout'] = steps[0]['with']['sparse-checkout'].replace(
        '/verification/cache-fixture-compiler-admission-v3/\n',
        '/verification/cache-fixture-compiler-admission-v3/\n'
        '/verification/cache-fixture-workflow-context-v4/\n').replace(old_name, new_name)
    for index in [1, 2, 5]:
        script = steps[index]['run']
        script = script.replace(
            'MIXER_COMPILER_ADMISSION_DIR="$GITHUB_WORKSPACE/verification/cache-fixture-compiler-admission-v3"\n',
            'MIXER_COMPILER_ADMISSION_DIR="$GITHUB_WORKSPACE/verification/cache-fixture-compiler-admission-v3"\n'
            'MIXER_WORKFLOW_CONTEXT_DIR="$GITHUB_WORKSPACE/verification/cache-fixture-workflow-context-v4"\n')
        script = script.replace('"$MIXER_COMPILER_ADMISSION_DIR/logs"\n',
                                '"$MIXER_COMPILER_ADMISSION_DIR/logs" "$MIXER_WORKFLOW_CONTEXT_DIR/logs"\n')
        script = script.replace('"$MIXER_COMPILER_ADMISSION_DIR/verify_candidate.py"',
                                '"$MIXER_WORKFLOW_CONTEXT_DIR/verify_candidate.py"')
        script = script.replace('python3 -B "$MIXER_COMPILER_ADMISSION_DIR/test_admission.py"',
                                'python3 -B "$MIXER_WORKFLOW_CONTEXT_DIR/test_context.py"\n'
                                'python3 -B "$MIXER_COMPILER_ADMISSION_DIR/test_admission.py"')
        steps[index]['run'] = script
    artifact = steps[6]['with']
    artifact['name'] = artifact['name'].replace('cache-fixture-compiler-admission-v3-',
                                               'cache-fixture-workflow-context-v4-')
    artifact['path'] = artifact['path'].replace(
        '${{ github.workspace }}/verification/cache-fixture-compiler-admission-v3/\n',
        '${{ github.workspace }}/verification/cache-fixture-compiler-admission-v3/\n'
        '${{ github.workspace }}/verification/cache-fixture-workflow-context-v4/\n').replace(old_name, new_name)
    return result


def validate_contract(document, original):
    need(document == expected_document(original), 'Workflow exceeds the authorized v3-to-v4 transformation')
    return validate(document)
