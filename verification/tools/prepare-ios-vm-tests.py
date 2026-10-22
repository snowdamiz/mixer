#!/usr/bin/env python3
"""Prepare a signed-app harness for unchanged owned VM Rust test assertions.

The Rust #[test] attributes are removed only so the same functions can be called
from an explicit, panic-containing C boundary inside an iOS development app.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--revision', required=True)
    p.add_argument('--test', choices=['table_memory', 'float', 'interpreter', 'review_boundaries', 'sessions'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', a.revision + '^{commit}'], cwd=ROOT, text=True).strip()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'
    source.mkdir()
    archive = subprocess.check_output(['git', 'archive', revision, 'vm', 'contracts/vm-profile-v1.json'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source, filter='data')
    rust = out / 'rust'
    (rust / 'src').mkdir(parents=True)
    test = source / f'vm/tests/{a.test}.rs'
    original = test.read_text()
    functions = re.findall(r'#\[test\]\s*fn (\w+)\(', original)
    assert functions and original.count('#[test]') == len(functions)
    assert '#[ignore' not in original
    adapted = original.replace('#[test]', '')
    calls = '\n'.join(f'        {name}(); println!("MIXER_VM_IOS_CASE_PASSED {name}");' for name in functions)
    adapted += f'''
#[no_mangle]
pub extern "C" fn mixer_qualification_run() -> u32 {{
    match std::panic::catch_unwind(|| {{
{calls}
        {len(functions)}u32
    }}) {{ Ok(count) => count, Err(_) => 0 }}
}}
'''
    (rust / 'src/lib.rs').write_text(adapted)
    shutil.copytree(source / 'vm/tests/common', rust / 'src/common')
    (rust / 'Cargo.toml').write_text('''[package]
name = "mixer-vm-qualification"
version = "0.1.0"
edition = "2021"
[lib]
crate-type = ["staticlib"]
[dependencies]
mixer-vm = { path = "../source/vm" }
[profile.release]
overflow-checks = true
panic = "unwind"
''')
    app = out / 'app'
    shutil.copytree(ROOT / 'verification/tools/ios-numeric', app)
    (app / 'lib').mkdir()
    (app / 'Host-Bridging.h').write_text('#include <stdint.h>\nuint32_t mixer_qualification_run(void);\n')
    (app / 'Host.swift').write_text(f'''import Foundation
import SwiftUI
@main struct VMQualification: App {{
    var body: some Scene {{ WindowGroup {{ Text("Mixer VM assertion qualification").task {{
        let count = await Task.detached(priority: .userInitiated) {{ mixer_qualification_run() }}.value
        print(count == {len(functions)} ? "MIXER_VM_IOS_TESTS_PASSED \\(count)" : "MIXER_VM_IOS_TESTS_FAILED \\(count)")
        fflush(nil)
        exit(count == {len(functions)} ? 0 : 1)
    }} }} }}
}}
''')
    project = app / 'NumericVM.xcodeproj/project.pbxproj'
    pbx = project.read_text().replace('-lmixer_vm ', '-lmixer_vm_qualification ')
    pbx = pbx.replace('dev.mixer.numericqualification', 'dev.mixer.vmtestqualification')
    pbx = pbx.replace('files = (A00000000000000000000018);', 'files = ();')
    project.write_text(pbx)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {'source_revision': revision, 'source_archive_sha256': hashlib.sha256(archive).hexdigest(),
        'test': a.test, 'test_functions': functions, 'original_test_sha256': digest(test),
        'adapted_test_sha256': digest(rust / 'src/lib.rs'),
        'adaptation': 'Remove #[test] registration only; original assertions unchanged; C catch_unwind wrapper invokes every function',
        'generator_sha256': digest(Path(__file__))}
    (out / 'prepared.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'directory': str(out), 'test_functions': len(functions)}, indent=2))


if __name__ == '__main__':
    main()
