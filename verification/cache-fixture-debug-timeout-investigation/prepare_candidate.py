#!/usr/bin/env python3
"""Create a sibling proposal only; never mutate the closed source pack."""
import difflib
import hashlib
import json
from pathlib import Path
import sys

def deny(event, args):
    if event in {'subprocess.Popen','os.system','os.posix_spawn','os.spawn',
                 'socket.__new__','socket.connect','os.kill','os.killpg'}:
        raise RuntimeError('Offline preparation forbids ' + event)
sys.addaudithook(deny)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'verification/swift-cache-state-ci/pack/source/regression/independent_tests.rs'
original = SOURCE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == '7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411'
start = original.index('fn run(f: &Fixture, framing: bool, label: &str) {')
end = original.index('\n#[test]', start)
old_run = original[start:end]
new_run = '''#[derive(Default)]
struct ContextPhaseTimes {
    prepare: std::time::Duration,
    analyze: std::time::Duration,
    report_assert: std::time::Duration,
    cleanup: std::time::Duration,
}

fn run_context_opened(
    files: (File, File, File, File), framing: bool, label: &str, path: &std::path::Path,
) -> ContextPhaseTimes {
    let (mut stream,mut profile,mut context,mut output)=files;
    let analyze_start=std::time::Instant::now();
    let result=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output);
    let analyze=analyze_start.elapsed();
    let report_start=std::time::Instant::now();
    output.seek(SeekFrom::Start(0)).unwrap(); let mut report=Vec::new(); output.read_to_end(&mut report).unwrap();
    match &result {
        Ok(outcome)=>{assert!(!outcome.stored_prefix_validated());assert!(!outcome.full_replay_accepted());},
        Err(error)=>{assert_eq!(error.reserved,0);assert!(report.len()<=REPORT);if report.len()==REPORT {assert_eq!(get(&report,4),0);}},
    }
    if framing { assert!(result.is_ok(),"expected framing observation {label}"); check_report(&report,true); }
    else if result.is_ok() {check_report(&report,false); assert_eq!(get(&report,3),3,"malformed vector admitted: {label}");}
    let report_assert=report_start.elapsed();
    let cleanup_start=std::time::Instant::now();
    drop((stream,profile,context,output));
    fs::remove_dir_all(path).unwrap();
    ContextPhaseTimes { prepare: std::time::Duration::ZERO, analyze, report_assert, cleanup: cleanup_start.elapsed() }
}

fn assert_shared_context_inputs(shared: &std::path::Path, baseline: &Fixture) {
    for (name,expected) in [("stream",&baseline.stream),("profile",&baseline.profile)] {
        let path=shared.join(name);
        let metadata=fs::metadata(&path).unwrap();
        assert!(metadata.is_file());
        assert!(metadata.permissions().readonly());
        assert_eq!(&fs::read(&path).unwrap(),expected,"shared context input bytes changed: {name}");
    }
}

fn run_context_case(
    bytes: &[u8], shared: &std::path::Path, label: &str,
    completed: &mut usize, total: &mut ContextPhaseTimes, started: std::time::Instant,
) {
    let prepare_start=std::time::Instant::now();
    let path=scratch(label);
    fs::write(path.join("context"),bytes).unwrap();
    let mut stream=File::open(shared.join("stream")).unwrap();
    let mut profile=File::open(shared.join("profile")).unwrap();
    let mut context=File::open(path.join("context")).unwrap();
    let mut output=OpenOptions::new().read(true).write(true).create_new(true).open(path.join("report")).unwrap();
    for file in [&mut stream,&mut profile,&mut context,&mut output] {
        assert_eq!(file.stream_position().unwrap(),0,"fresh offset-zero handle required");
    }
    let prepare=prepare_start.elapsed();
    let phases=run_context_opened((stream,profile,context,output),false,label,&path);
    total.prepare+=prepare;total.analyze+=phases.analyze;
    total.report_assert+=phases.report_assert;total.cleanup+=phases.cleanup;
    *completed+=1;
    if *completed%64==0 || *completed==1003 {
        eprintln!("context_progress completed={}/1003 elapsed_ms={} prepare_ms={} analyze_ms={} report_assert_ms={} cleanup_ms={}",
            *completed,started.elapsed().as_millis(),total.prepare.as_millis(),total.analyze.as_millis(),
            total.report_assert.as_millis(),total.cleanup.as_millis());
    }
}
'''
candidate = original[:end] + '\n' + new_run + original[end:]
assert old_run in candidate
start = candidate.index('fn context_schema_scalar_reserved_and_lengths() {')
end = candidate.index('\n#[test]', start)
old_method = candidate[start:end]
new_method = old_method.replace('    let baseline=Fixture::new();', '''    let started=std::time::Instant::now();
    let baseline=Fixture::new();
    let shared=scratch("context-shared-inputs");
    for (name,bytes) in [("stream",&baseline.stream),("profile",&baseline.profile)] {
        let path=shared.join(name);
        fs::write(&path,bytes).unwrap();
        let mut permissions=fs::metadata(&path).unwrap().permissions();
        permissions.set_readonly(true);
        fs::set_permissions(&path,permissions).unwrap();
    }
    assert_shared_context_inputs(&shared,&baseline);
    let mut completed=0usize;
    let mut total=ContextPhaseTimes::default();''')
new_method = new_method.replace('let mut f=baseline.clone();f.context(word,value);run(&f,false,&format!("context-{word}-{value}"));', 'let mut context=baseline.context.clone();put(&mut context,word,value);run_context_case(&context,&shared,&format!("context-{word}-{value}"),&mut completed,&mut total,started);')
new_method = new_method.replace('let mut f=baseline.clone();f.context(word,1);run(&f,false,&format!("context-reserved-{word}"));', 'let mut context=baseline.context.clone();put(&mut context,word,1);run_context_case(&context,&shared,&format!("context-reserved-{word}"),&mut completed,&mut total,started);')
new_method = new_method.replace('let mut f=baseline.clone();f.context.resize(len,0);run(&f,false,&format!("context-length-{len}"));', 'let mut context=baseline.context.clone();context.resize(len,0);run_context_case(&context,&shared,&format!("context-length-{len}"),&mut completed,&mut total,started);')
assert new_method.endswith('\n}\n')
new_method = new_method[:-3] + '''
    assert_eq!(completed,1003,"complete ordered context vector coverage");
    assert_shared_context_inputs(&shared,&baseline);
    fs::remove_dir_all(&shared).unwrap();
}
'''
assert 'baseline.clone()' not in new_method and new_method.count('run_context_case(') == 3
candidate = candidate[:start] + new_method + candidate[end:]
destination = HERE / 'candidate/source/regression/independent_tests.rs'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(candidate)
diff = ''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),
    fromfile='a/verification/swift-cache-state-ci/pack/source/regression/independent_tests.rs',
    tofile='b/verification/swift-cache-state-ci/pack/source/regression/independent_tests.rs'))
(HERE/'context-harness-proposal.diff').write_text(diff)
receipt = {'schema':1,'status':'sibling-source-proposal-only-not-compiled',
    'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
    'candidate':str(destination.relative_to(ROOT)),'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
    'diff_sha256':hashlib.sha256(diff.encode()).hexdigest(),
    'product_sources_changed':False,'closed_pack_or_manifest_changed':False,
    'compiler_or_runtime_executed':False,
    'failure_retention':'Shared input files remain under owned test scratch until all vectors and final content/read-only assertions succeed. Existing cleanup inventory recursively hashes/retains unknown non-product files, so failed shared files are retained by the unchanged runner.',
    'success_cleanup':'Each vector retains its existing assertions and handle closure before removing its case directory; shared input directory is removed only after complete coverage and final content/read-only checks.',
    'required_before_acceptance':['Source review','Closed candidate pack manifest and runner pin updated coherently by root','Real compiler checks','Focused runner controls','Complete exact-source fixture closure on the declared compiler']}
(HERE/'candidate-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'candidate_sha256':receipt['candidate_sha256']},sort_keys=True))
