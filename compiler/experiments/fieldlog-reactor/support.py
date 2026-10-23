"""Non-authorizing source mapping, observation and descriptor diagnostics."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'compiler'))
from qualification_support import model_observations, strict_json
sys.path.insert(0, str(ROOT / 'compiler/experiments/profile-budget'))
from analyze import Reader

HARNESS_SHA256 = '344168377051c105e60eb84388c54d48c2259224157ac68a1f877ac36a8e7c59'


def source_mapping(corpus, wrapper):
    if hashlib.sha256(corpus).hexdigest() != HARNESS_SHA256:
        raise ValueError('original corpus identity changed')
    marker = b'let now = Date(timeIntervalSince1970: 1_792_627_200)\n'
    declaration = b'private func runFieldLogCorpus() throws {\n'
    end = b'}\n\n// Swift errors must not cross a C-compatible boundary.'
    if wrapper.count(declaration) != 1 or wrapper.count(end) != 1:
        raise ValueError('ambiguous wrapper source map')
    body = corpus[corpus.index(marker):]
    actual = wrapper.split(declaration, 1)[1].split(end, 1)[0]
    if actual != body:
        raise ValueError('wrapper changed original corpus body')
    receipt = corpus[corpus.index(b'struct Receipt:'):corpus.index(marker)].rstrip()
    wrapped_receipt = wrapper[wrapper.index(b'struct Receipt:'):wrapper.index(b'// The body between')].rstrip()
    if receipt != wrapped_receipt:
        raise ValueError('wrapper changed Receipt fields')
    if wrapper.count(b'@_cdecl(') != 1 or b'@_cdecl("mixer_fieldlog_corpus_v1")' not in wrapper:
        raise ValueError('wrapper C export differs')
    if b'import Foundation\nimport FieldLogModels\n' not in wrapper:
        raise ValueError('wrapper imports differ')
    return dict(bodySHA256=hashlib.sha256(body).hexdigest(), bodyBytes=len(body),
                receiptSHA256=hashlib.sha256(receipt).hexdigest(), receiptBytes=len(receipt),
                originalBodyStartLine=corpus[:corpus.index(marker)].count(b'\n') + 1,
                wrapperBodyStartLine=wrapper[:wrapper.index(declaration)].count(b'\n') + 2,
                exactBodyBytes=True, exactReceiptBytes=True)


def observations(output, count, expected=None):
    lines = output.splitlines()
    if len(lines) != count:
        raise ValueError('missing, extra or merged observation lines')
    values = [model_observations(strict_json(line)) for line in lines]
    if expected is not None and any(item != expected for item in values):
        raise ValueError('complete observation object differs from oracle')
    return values


def descriptors(data):
    """Exact scalar signatures and exports; no body/type/admission validation."""
    if len(data) > 128 * 1024 * 1024:
        raise ValueError('descriptor source ceiling exceeded')
    reader = Reader(data)
    if bytes(reader.take(8)) != b'\0asm\x01\0\0\0':
        raise ValueError('not Wasm version one')
    types, functions, imports, exports = [], [], [], []
    seen = set()
    last = 0
    start = None
    scalar = {0x7f: 'i32', 0x7e: 'i64', 0x7d: 'f32', 0x7c: 'f64'}

    def count(section, limit):
        value = section.uint()
        if value > limit:
            raise ValueError('descriptor vector ceiling exceeded')
        return value

    def name(section):
        return bytes(section.take(count(section, 4096))).decode('utf-8')

    def values(section):
        result = []
        for _ in range(count(section, 256)):
            value = section.byte()
            if value not in scalar:
                raise ValueError('non-scalar signature outside diagnostic scope')
            result.append(scalar[value])
        return result

    while reader.position < len(data):
        section_id, size = reader.byte(), reader.uint()
        section = Reader(reader.take(size))
        if section_id > 11 or (section_id and (section_id in seen or section_id < last)):
            raise ValueError('unsupported, duplicate or unordered descriptor section')
        if section_id:
            seen.add(section_id)
            last = section_id
        if section_id == 1:
            for _ in range(count(section, 1024)):
                if section.byte() != 0x60:
                    raise ValueError('unsupported function type')
                types.append(dict(parameters=values(section), results=values(section)))
        elif section_id == 2:
            for _ in range(count(section, 256)):
                module, item = name(section), name(section)
                if section.byte() != 0:
                    raise ValueError('non-function import outside diagnostic scope')
                type_index = section.uint()
                imports.append(dict(module=module, name=item, function=len(functions), typeIndex=type_index))
                functions.append(type_index)
        elif section_id == 3:
            functions.extend(section.uint() for _ in range(count(section, 100_000)))
        elif section_id == 7:
            for _ in range(count(section, 256)):
                item, kind, index = name(section), section.byte(), section.uint()
                if kind not in (0, 2):
                    raise ValueError('export kind outside diagnostic scope')
                exports.append(dict(name=item, kind='function' if kind == 0 else 'memory', index=index))
            if len({row['name'] for row in exports}) != len(exports):
                raise ValueError('duplicate descriptor export')
        elif section_id == 8:
            start = section.uint()
        else:
            continue
        section.end()
    if any(index >= len(types) for index in functions):
        raise ValueError('function type index exceeds descriptor types')
    for item in imports:
        item['signature'] = types[item['typeIndex']]
    for item in exports:
        if item['kind'] == 'function':
            if item['index'] >= len(functions):
                raise ValueError('export function index exceeds descriptor functions')
            item['typeIndex'] = functions[item['index']]
            item['signature'] = types[item['typeIndex']]
    return dict(authorization=False, scope='bounded scalar descriptor inventory; no executable validation',
                typeCount=len(types), functionCount=len(functions), startFunction=start,
                imports=imports, exports=exports)
