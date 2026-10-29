"""Restricted workflow data controls; neither an official validator nor execution.

The YAML subset parser and simple expression checker are copied from the earlier
envelope context correction, with only comment skipping and simple inline lists
added for this frozen proposal. Only this proposal's supported data is accepted.
"""
import hashlib,json
from copy import deepcopy
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PARENT='verification/swift-pin-bitmap-format-lint-admission/'
SIBLING='verification/swift-pin-bitmap-format-lint-host-correction/'
PARENT_SEAL='862f614a957aa76eb332e3f27ca2f922e0a812ebe51c6f766836f99a1d36f33f'
RUSTUP_HOME='${{ runner.temp }}/swift-pin-bitmap-format-lint-v1-toolchain'
INSTALL='Install exact hosted formatting and Clippy tools'
DRIVER='Five bounded formatting and lint children'
HISTORICAL=('DECISION.md','admit.py','workflow.yml','root_controls.py','seal.json','root-controls-result.json','receipt.json','source-basis.json')


def need(value, message):
    if not value:
        raise ValueError(message)


def scalar(value):
    if value.startswith('['):
        need(value.endswith(']'), 'Unclosed inline list')
        items=[item.strip() for item in value[1:-1].split(',')]
        need(items and all(item and all(c.isalnum() or c in '_-' for c in item) for item in items),
             'Unsupported inline list')
        return items
    need(value and value[0] not in '&*!>|{', 'Unsupported YAML scalar')
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
        while pos < len(lines) and (not lines[pos].strip() or lines[pos].lstrip().startswith('#')):
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
        parts = expression.split('.')
        need(len(parts) == 2 and all(part and all(c.isalnum() or c == '_' for c in part)
                                     and not part[0].isdigit() for part in parts),
             'Unsupported expression grammar at ' + location)
        need(parts[0] in allowed, 'Context ' + parts[0] + ' unavailable at ' + location)
        references.append({'location': location, 'expression': expression})
        offset = end + 2


def validate(document):
    rules=json.loads((HERE/'context-rules.json').read_bytes())['contexts']
    references=[]
    def env(value,kind,location):
        need(isinstance(value,dict),'Environment must be a mapping at '+location)
        for key,item in value.items():
            need(isinstance(item,str),'Environment must contain strings at '+location)
            references.extend(expressions(item,rules[kind],location+'.'+key))
    need(isinstance(document,dict),'Workflow must be a mapping')
    if 'env' in document:env(document['env'],'workflow-env','env')
    if 'concurrency' in document:
        need(isinstance(document['concurrency'],dict),'Concurrency must be a mapping')
        references.extend(expressions(document['concurrency'].get('group'),rules['workflow-concurrency'],'concurrency.group'))
    need(isinstance(document.get('jobs'),dict),'Jobs must be a mapping')
    for name,job in document['jobs'].items():
        need(isinstance(job,dict),'Job must be a mapping')
        if 'env' in job:env(job['env'],'job-env','jobs.'+name+'.env')
        need(isinstance(job.get('steps'),list),'Steps must be a sequence')
        for index,step in enumerate(job['steps']):
            location='jobs.'+name+'.steps.'+str(index)
            need(isinstance(step,dict),'Step must be a mapping')
            if 'env' in step:env(step['env'],'step-env',location+'.env')
            for key in ('name','uses','run'):
                if key in step:references.extend(expressions(step[key],rules['steps'],location+'.'+key))
            if 'with' in step:
                need(isinstance(step['with'],dict),'Action inputs must be a mapping')
                for key,item in step['with'].items():
                    references.extend(expressions(item,rules['steps'],location+'.with.'+key))
    return {'expressionReferences':references,'officialValidatorExecuted':False,'workflowOrShellExecuted':False,
            'scope':'restricted data parsing and frozen GitHub context allowlists; not full workflow validation'}


def expected_document(original):
    result=deepcopy(original);job=result['jobs']['diagnose']
    need(job.pop('env')=={'RUSTUP_HOME':RUSTUP_HOME},'Frozen parent job environment differs')
    for step in job['steps']:
        if step.get('name') in (INSTALL,DRIVER):
            step.setdefault('env',{})['RUSTUP_HOME']=RUSTUP_HOME
        if 'run' in step:step['run']=step['run'].replace(PARENT,SIBLING)
        if 'with' in step:
            values=step['with']
            if 'sparse-checkout' in values:values['sparse-checkout']+='/'+SIBLING+'\n'
            if 'path' in values:values['path']=values['path'].replace(PARENT,SIBLING)
    return result


def validate_contract(document,original):
    result=validate(document)
    need(document==expected_document(original),'Workflow exceeds the authorized host correction')
    job=document['jobs']['diagnose'];need('env' not in job,'Rustup home must be step-local')
    consuming=[step for step in job['steps'] if step.get('name') in (INSTALL,DRIVER)]
    need(len(consuming)==2 and all(step['env']['RUSTUP_HOME']==RUSTUP_HOME for step in consuming),
         'Both consuming steps require exact Rustup home')
    return result


def sparse_patterns(document):
    steps=document['jobs']['diagnose']['steps']
    checkout=[s for s in steps if s.get('uses')=='actions/checkout@v4']
    need(len(checkout)==1,'Exactly one pinned checkout')
    patterns=checkout[0]['with']['sparse-checkout'].splitlines()
    need(all(p.startswith('/') and not any(c in p for c in '*!?[]\\') and '..' not in p.split('/') for p in patterns),
         'Only explicit anchored sparse paths supported')
    return patterns


def require_sparse_contains(document,paths):
    patterns=sparse_patterns(document);missing=[]
    for path in sorted(set(paths)):
        need(path and not path.startswith('/') and '..' not in path.split('/'),'Canonical relative sparse member')
        if not any(path==p[1:] or (p.endswith('/') and path.startswith(p[1:])) for p in patterns):missing.append(path)
    need(not missing,'Sparse checkout omits inputs: '+', '.join(missing))
    return {'requiredPaths':sorted(set(paths)),'patterns':patterns,'missing':missing,
            'scope':'anchored finite sparse pattern closure over actual materializer reads and local control sources'}


def verify_parent():
    def raw(path):
        need(path.is_file() and not path.is_symlink(),'Regular bound source required: '+str(path))
        return path.read_bytes()
    def row(value):return {'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
    parent=ROOT/PARENT;seal_raw=raw(parent/'seal.json')
    need(hashlib.sha256(seal_raw).hexdigest()==PARENT_SEAL,'Frozen parent seal changed')
    seal=json.loads(seal_raw);need(len(seal['files'])==10,'Frozen parent member roster changed')
    need(all(row(raw(parent/n))==r for n,r in seal['files'].items()),'Frozen parent member changed')
    need(all(raw(HERE/'historical'/n)==raw(parent/n) for n in HISTORICAL),'Historical preimage differs')
    need(all(raw(HERE/n)==raw(parent/n) for n in ('bounded_commands.py','offline.py')),'Byte-identical helper changed')
    return {'sealSHA256':PARENT_SEAL,'membersVerified':10,'historicalPreimagesVerified':list(HISTORICAL),
            'byteIdenticalHelpers':['bounded_commands.py','offline.py'],'historicalResultsAreCurrentEvidence':False}
