#!/usr/bin/env python3
"""Independent extracted-helper boundaries, fixture semantics and privacy probes."""
import json
from pathlib import Path
import review as r

def extract_function(text, signature):
    start = text.index(signature)
    opening = text.index('{',start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'

def prepare():
    dest = r.OUT / 'probes'
    dest.mkdir(exist_ok=True)
    codec_path = 'vm/src/experimental_swift_reactor/diagnostic_result_v1.rs'
    codec = (r.SOURCE/codec_path).read_text()
    function = extract_function(codec,'fn write_words(')
    source = '#![forbid(unsafe_code)]\n' + function + r'''
#[test]
fn actual_helper_unaligned_lengths_word_counts_and_tails() {
    let mut lengths: Vec<usize> = (0..=145).collect();
    lengths.extend([255,256,257,511,512,513,1023,1024,1025,2047,2048,2049]);
    let mut counts: Vec<usize> = (0..=20).collect();
    counts.extend([63,64,65,255,256,257]);
    let mut cases = 0u64;
    let mut checked_bytes = 0u64;
    let mut unaligned_cases = 0u64;
    let mut tail_cases = 0u64;
    let mut fewer_words_cases = 0u64;
    let mut excess_words_cases = 0u64;
    for length in lengths {
        for &count in &counts {
            let words: Vec<u64> = (0..count).map(|n| match n % 8 {
                0 => 0,
                1 => u64::MAX,
                2 => 0x0123_4567_89ab_cdef,
                3 => 0x8000_0000_0000_0001,
                4 => 1u64 << (n % 64),
                5 => 0x00ff_aa55_f00f_3399,
                _ => (n as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15).rotate_left((n % 64) as u32),
            }).collect();
            for offset in 0..16 {
                let size = offset + length + 17;
                let before: Vec<u8> = (0..size).map(|n| (n as u8).wrapping_mul(37).wrapping_add(0x5b)).collect();
                let mut actual = before.clone();
                write_words(&mut actual[offset..offset + length], &words);
                // Independent byte oracle: index and shift scalar words. It
                // uses neither byte-conversion methods nor chunk iteration.
                let written = std::cmp::min(length / 8,count) * 8;
                for index in 0..size {
                    let want = if index >= offset && index - offset < written {
                        let relative = index - offset;
                        ((words[relative / 8] >> (8 * (relative % 8))) & 255) as u8
                    } else {
                        before[index]
                    };
                    assert_eq!(actual[index],want,"length={length} words={count} offset={offset} byte={index}");
                }
                cases += 1;
                checked_bytes += size as u64;
                unaligned_cases += u64::from(actual[offset..].as_ptr().align_offset(8) != 0);
                tail_cases += u64::from(length % 8 != 0);
                fewer_words_cases += u64::from(count < length / 8);
                excess_words_cases += u64::from(count > length / 8);
            }
        }
    }
    assert_eq!(cases, 68_256);
    assert!(unaligned_cases > 0 && tail_cases > 0 && fewer_words_cases > 0 && excess_words_cases > 0);
    println!("BOUNDARIES cases={cases} checked_bytes={checked_bytes} unaligned_cases={unaligned_cases} tail_cases={tail_cases} fewer_words_cases={fewer_words_cases} excess_words_cases={excess_words_cases}");
}
'''
    (dest/'scalar-boundaries.rs').write_text(source)
    row_path = 'vm/src/experimental_swift_reactor/diagnostic_profile_tests.rs'
    row = (r.SOURCE/row_path).read_text()
    begin = row.index('struct OwnedDirectory(PathBuf);')
    end = row.index('fn assert_wire(',begin)
    fixture = row[begin:end]
    fixture_source = '#![forbid(unsafe_code)]\nuse std::path::PathBuf;\nuse std::fs::{self,File,OpenOptions};\nuse std::io::{self,Write};\n' + fixture + r'''
#[test]
fn exact_fixture_refuses_collisions_preserves_unowned_and_cleans_normal_and_unwind() {
    let temporary = std::env::temp_dir();
    let collision = temporary.join(format!("mixer-diagnostic-profile-{}-0", std::process::id()));
    fs::create_dir(&collision).unwrap();
    fs::write(collision.join("preserve.bin"), b"collision-sentinel").unwrap();
    let normal;
    {
        let directory = OwnedDirectory::new();
        normal = directory.0.clone();
        assert_ne!(normal,collision);
        assert!(normal.ends_with(format!("mixer-diagnostic-profile-{}-1",std::process::id())));
        let mut file = directory.fresh("normal.bin");
        file.write_all(b"normal-data").unwrap();
        let result = std::panic::catch_unwind(|| directory.fresh("normal.bin"));
        assert!(result.is_err());
        assert_eq!(fs::read(normal.join("normal.bin")).unwrap(),b"normal-data");
        // Normal lexical reverse-drop order closes File before OwnedDirectory.
    }
    assert!(!normal.exists());
    assert_eq!(fs::read(collision.join("preserve.bin")).unwrap(), b"collision-sentinel");
    let unwind = std::cell::RefCell::new(None);
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let directory = OwnedDirectory::new();
        *unwind.borrow_mut() = Some(directory.0.clone());
        let mut file = directory.fresh("unwind.bin");
        file.write_all(b"unwind-data").unwrap();
        panic!("intentional independently checked fixture unwind");
    }));
    assert!(result.is_err());
    assert!(!unwind.borrow().as_ref().unwrap().exists());
    assert_eq!(fs::read(collision.join("preserve.bin")).unwrap(), b"collision-sentinel");
    fs::remove_file(collision.join("preserve.bin")).unwrap();
    fs::remove_dir(collision).unwrap();
    println!("FIXTURE collision_skip=pass create_new_preservation=pass normal_cleanup=pass unwind_cleanup=pass unowned_sentinel_preserved=pass");
}
'''
    (dest/'fixture-ownership.rs').write_text(fixture_source)
    sources = {
        'public-validator-positive.rs':'use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor; pub fn observe(p: &ValidatedSwiftReactor) -> usize { p.source().len() }\n',
        'codec-private-negative.rs':'use mixer_vm::experimental_swift_reactor::diagnostic_result_v1::decode_result_v1;\n',
        'row-private-negative.rs':'use mixer_vm::experimental_swift_reactor::diagnostic_profile::write_profile_row_body_v1;\n',
    }
    for name,text in sources.items():
        (dest/name).write_text(text)
    r.write(r.OUT/'extracted-source-attribution.json',{'schema':1,
        'scalar':{'path':codec_path,'source':r.member(r.SOURCE,codec_path),'exact_function_sha256':r.sha(function.encode()),
                  'exact_function':function,'harness':r.member(r.OUT,'probes/scalar-boundaries.rs'),
                  'oracle':'scalar index and bit shifts; full prefix, suffix, short word count and incomplete trailing byte preservation'},
        'fixture':{'path':row_path,'source':r.member(r.SOURCE,row_path),'exact_fixture_sha256':r.sha(fixture.encode()),
                   'exact_fixture':fixture,'harness':r.member(r.OUT,'probes/fixture-ownership.rs'),
                   'new_native_or_runtime_authority':False}})
    print(json.dumps({'prepare':'pass','scalar_function_sha256':r.sha(function.encode()),'fixture_sha256':r.sha(fixture.encode())}),flush=True)

def boundaries():
    probes = r.OUT/'probes'
    binaries = r.SCRATCH/'probe-binaries'
    binaries.mkdir(exist_ok=True)
    for name in ('scalar-boundaries','fixture-ownership'):
        for mode,flags in [('debug',[]),('release',['-C','opt-level=3','-C','overflow-checks=yes'])]:
            binary = binaries/f'{name}-{mode}'
            r.run(f'{name}-{mode}-compile',[str(r.TOOLS/'rustc'),'--edition=2021','--test','-D','warnings',*flags,
                                          str(probes/f'{name}.rs'),'-o',str(binary)],60)
            r.run(f'{name}-{mode}-execute',[str(binary),'--nocapture','--test-threads=1'],60)

def privacy():
    probes = r.OUT/'probes'
    binaries = r.SCRATCH/'probe-binaries'
    binaries.mkdir(exist_ok=True)
    r.run('private-probe-library-build',[str(r.TOOLS/'cargo'),'build','--offline','--locked',
                                       '--manifest-path',str(r.SOURCE/'vm/Cargo.toml'),'--lib',
                                       '--features','experimental-swift-reactor'],180)
    deps=r.SCRATCH/'target/debug/deps'
    library=deps/'libmixer_vm.rlib'
    assert library.is_file()
    for name,expected in [('public-validator-positive',0),('codec-private-negative',1),('row-private-negative',1)]:
        receipt=r.run(name,[str(r.TOOLS/'rustc'),'--edition=2021','--crate-name',name.replace('-','_'),
                           '--crate-type=lib','--emit=metadata','--extern',f'mixer_vm={library}',
                           '-L',f'dependency={deps}','--out-dir',str(binaries),str(probes/f'{name}.rs')],30,expected)
        stderr=(r.OUT/'commands'/name/'stderr').read_text()
        if expected:
            assert 'E0603' in stderr and 'module' in stderr and 'private' in stderr
    print(json.dumps({'supplement':'pass','privacy_positive':1,'privacy_negative':2}),flush=True)

if __name__=='__main__':
    import sys
    {'prepare':prepare,'boundaries':boundaries,'privacy':privacy}[sys.argv[1]]()
