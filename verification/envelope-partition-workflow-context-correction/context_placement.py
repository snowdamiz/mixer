"""Narrow data-only workflow/context check; no official validator execution.

Parser and simple-property expression functions are copied byte-for-byte from
cache-fixture-workflow-context-v4/workflow_context.py. Their frozen source and
function hashes are recorded in correction-basis.json. No workflow or shell is
executed. This check does not authorize any runtime, release or dispatch.
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


PARENT = 'verification/envelope-partition-independent-review/'
SIBLING = 'verification/envelope-partition-workflow-context-correction/'
RUNNER_ENV = {'MIXER_RUNNER_ENVIRONMENT': '${{ runner.environment }}'}
ADMISSION_STEPS = (
    'Bind exact source and existing direct compiler, then invoke once',
    'Source postflight and complete terminal replay',
)


def validate(document):
    """Check environment contexts and the small expression grammar, not YAML schema."""
    rules = json.loads((HERE / 'context-rules.json').read_bytes())
    references = []

    def env(value, kind, location):
        need(isinstance(value, dict), 'Environment must be a mapping at ' + location)
        for key, item in value.items():
            need(isinstance(item, str), 'Environment must contain strings at ' + location)
            references.extend(expressions(item, rules['contexts'][kind], location + '.' + key))

    need(isinstance(document, dict), 'Workflow must be a mapping')
    if 'env' in document:
        env(document['env'], 'workflow-env', 'env')
    need(isinstance(document.get('jobs'), dict), 'Jobs must be a mapping')
    for name, job in document['jobs'].items():
        need(isinstance(job, dict), 'Job must be a mapping')
        if 'env' in job:
            env(job['env'], 'job-env', 'jobs.' + name + '.env')
        need(isinstance(job.get('steps'), list), 'Steps must be a sequence')
        for index, step in enumerate(job['steps']):
            location = 'jobs.' + name + '.steps.' + str(index)
            need(isinstance(step, dict), 'Step must be a mapping')
            if 'env' in step:
                env(step['env'], 'step-env', location + '.env')
            for key in ('name', 'uses', 'run'):
                if key in step:
                    references.extend(expressions(step[key], rules['contexts']['steps'], location + '.' + key))
            if 'with' in step:
                need(isinstance(step['with'], dict), 'Action inputs must be a mapping')
                for key, item in step['with'].items():
                    references.extend(expressions(item, rules['contexts']['steps'], location + '.with.' + key))
    return {'expression_references': references,
            'scope': 'restricted data parsing and frozen official environment-context allowlists only',
            'official_validator_executed': False, 'workflow_or_shell_executed': False}


def expected_document(original):
    """The complete authorized transformation of the frozen parent workflow."""
    from copy import deepcopy
    result = deepcopy(original)
    job = result['jobs']['one-complete-host-fixture']
    need(job['env'].pop('MIXER_RUNNER_ENVIRONMENT') == RUNNER_ENV['MIXER_RUNNER_ENVIRONMENT'],
         'Frozen parent runner expression differs')
    for step in job['steps']:
        if step.get('name') in ADMISSION_STEPS:
            need('env' not in step, 'Frozen parent admission environment differs')
            step['env'] = dict(RUNNER_ENV)
        if 'run' in step:
            step['run'] = step['run'].replace(PARENT, SIBLING)
        if 'with' in step:
            for key in ('sparse-checkout', 'path'):
                if key in step['with']:
                    step['with'][key] = step['with'][key].replace(PARENT, SIBLING)
        if step.get('name') == 'Independent guarded source controls':
            step['run'] += ('python3 -B ' + SIBLING + 'test_context.py\n'
                            'python3 -B ' + SIBLING + 'verify_candidate.py --installed\n')
    return result


def validate_contract(document, original):
    result = validate(document)
    need(document == expected_document(original), 'Workflow exceeds the authorized context correction')
    job = document['jobs']['one-complete-host-fixture']
    need('MIXER_RUNNER_ENVIRONMENT' not in job['env'], 'Runner environment must be step-local')
    admitted = [step for step in job['steps'] if step.get('name') in ADMISSION_STEPS]
    need(len(admitted) == 2 and all(step.get('env') == RUNNER_ENV for step in admitted),
         'Both context-consuming admission steps require exact runner environment')
    return result
