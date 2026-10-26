#!/usr/bin/env python3
"""Bind retained targeted runtime frames to exact source/class/descriptor/BCI tables.

This checks evidence identity only. It cannot qualify unexecuted matrix rows.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent


def record(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    tables = {}
    for path in sorted((HERE / 'targeted-8').glob('02-bytecode-*.stdout')):
        text = path.read_text()
        class_name = re.search(r'^.*?class (dev\.mixer\.android\.[^ ]+)', text, re.M).group(1)
        methods = {}
        header = ''
        current = None
        for line in text.splitlines():
            if line.startswith('  ') and not line.startswith('    ') and '(' in line and line.endswith(';'):
                header = line.strip()
                current = None
            if line.strip().startswith('descriptor: ('):
                descriptor = line.strip().split(': ', 1)[1]
                method = header.split('(', 1)[0].split()[-1].rsplit('.', 1)[-1]
                current = dict(instructions={}, line_numbers=[])
                methods[(method, descriptor)] = current
            if current is not None:
                instruction = re.fullmatch(r'\s+(\d+):\s+(.+)', line)
                source_line = re.fullmatch(r'\s+line (\d+): (\d+)', line)
                if instruction:
                    current['instructions'][int(instruction[1])] = instruction[2]
                if source_line:
                    current['line_numbers'].append((int(source_line[2]), int(source_line[1])))
        tables[class_name] = (path, methods)
    bindings = []
    reference_classes = json.loads((HERE / 'targeted-8/compiled-class-hashes.json').read_text())
    compile_inputs = json.loads((HERE / 'targeted-8/01-compile.command.json').read_text())['source_map']
    seen = set()
    for output in sorted(HERE.glob('targeted-*/03-*.stdout')):
        for raw in output.read_text().splitlines():
            event = json.loads(raw)
            for key, value in event.items():
                if not isinstance(value, list):
                    continue
                for frame in value:
                    if not isinstance(frame, str) or not frame.startswith('dev.mixer.android.'):
                        continue
                    if (str(output), frame) in seen:
                        continue
                    seen.add((str(output), frame))
                    head, position = frame.split('@', 1)
                    qualified_method, descriptor_tail = head.split('(', 1)
                    class_name, method = qualified_method.rsplit('.', 1)
                    descriptor = '(' + descriptor_tail
                    bci, source_line = map(int, position.split(':'))
                    table_path, methods = tables[class_name]
                    method_table = methods[(method, descriptor)]
                    instruction = method_table['instructions'][bci]
                    mapped_line = max((pair for pair in method_table['line_numbers'] if pair[0] <= bci), key=lambda x:x[0])[1]
                    assert mapped_line == source_line, (frame, mapped_line)
                    class_path = class_name.replace('.', '/') + '.class'
                    original_classes = json.loads((output.parent / 'compiled-class-hashes.json').read_text())
                    assert original_classes[class_path] == reference_classes[class_path], class_path
                    basename = class_name.split('.')[-1].split('$')[0]
                    source_path = 'candidate-2/source/native/android/app/src/dev/mixer/android/' + basename + '.java'
                    assert record(HERE / source_path) == compile_inputs[source_path]
                    bindings.append(dict(runtime_output=str(output.relative_to(HERE)), runtime_frame=frame,
                        javap_output=str(table_path.relative_to(HERE)), javap_sha256=record(table_path)['sha256'],
                        class_path=class_path, compiled_class=reference_classes[class_path],
                        source_path=source_path, source=compile_inputs[source_path], instruction=instruction,
                        descriptor=descriptor, bytecode_index=bci, line=source_line,
                        original_and_reference_class_bytes_equal=True))
    result = dict(schema=1, scope='Identity bindings for retained targeted witnesses only; zero complete-matrix claims',
        reference_compilation='targeted-8/01-compile.command.json', bindings=bindings,
        bound_runtime_frames=len(bindings), duplicate_baseline_site_resolution='pending for full matrix')
    (HERE / 'runtime-frame-bindings.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='exact-targeted-frame-bindings-verified', frames=len(bindings), product_cases_run=0)))


if __name__ == '__main__':
    main()
