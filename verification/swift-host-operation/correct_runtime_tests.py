#!/usr/bin/env python3
from pathlib import Path
import collect as c
import shutil,json
p=c.HERE;vm=c.source('candidate');c.archive('historical-first-runtime',vm)
for n in['inventory-schema.json','function-manifest.json','closure-captures.json','positive-positions.rs','candidate.patch','changed-files.json','frozen-identity.json','actual-closure-layouts.json','negative-borrows.json']:
 if(p/n).exists():shutil.copy2(p/n,p/('historical-first-'+n))
f=vm/'src/experimental_swift_reactor/frame_operations.rs';t=f.read_text();old='self.phase.push_value(Value::I32(i32::from(official_errno)))';new='''#[cfg(not(test))]
        { self.phase.push_value(Value::I32(i32::from(official_errno))) }
        #[cfg(test)]
        {
            let old = super::tests::before_result_push(self.phase.operation.control);
            let result = self.phase.push_value(Value::I32(i32::from(official_errno)));
            super::tests::after_result_push(self.phase.operation.control, old);
            result
        }''';assert t.count(old)==1;f.write_text(t.replace(old,new))
f=vm/'src/experimental_swift_reactor/host_operation_tests.rs';t=f.read_text();t=t.replace('assert_eq!(report.first_failure, Some(failure));','assert_eq!(report.first_failure.unwrap().at_failure, failure.at_failure);\n        assert_eq!(report.first_failure.unwrap().code, failure.code);\n        assert!(report.first_failure.unwrap().after_cleanup.is_some());');f.write_text(t);(p/'tests.rs').write_text(t)
# Existing additive-envelope assertions need the additional class; accepted fields are untouched.
for name in['frame_operations_tests.rs','memory_operations_tests.rs','bulk_memory_operations_tests.rs']:
 f=vm/'src/experimental_swift_reactor'/name;t=f.read_text();needle='memory_growth_operations::ACTIVE_BYTES';assert t.count(needle)==1,(name,t.count(needle));path='host_runtime_import::ACTIVE_BYTES'if name=='frame_operations_tests.rs'else'super::super::host_runtime_import::ACTIVE_BYTES';t=t.replace(needle,needle+' + '+path);f.write_text(t)
c.archive('runtime-second-draft',vm)
# Retain the first runtime artifact identity even though its suite failed.
name='runtime-swift-debug';d=p/'artifacts'/name;artifact=json.loads((d/'cargo-artifact.json').read_text());exe=Path(artifact['executable']);import gzip
before=c.sha(gzip.decompress((d/'executable.gz').read_bytes()));after=c.sha(exe.read_bytes());assert before==after
c.save('artifacts/'+name+'/identity.json',dict(exactExecutablePath=str(exe),executableBeforeRunSHA256=before,executableAfterRunSHA256=after,executableSHA256=before,executableBytes=exe.stat().st_size,cargoArtifactFresh=artifact['fresh'],targetCreatedEmpty=True,sourceTreeSHA256=c.digest(json.loads((p/'historical-first-runtime-source-manifest.json').read_text())),failedSuite=True,fullUnitTestCount=len(json.loads((d/'test-list.json').read_text())),beforeRunDigestDerivedFromRetainedPreRunCompressedCopy=True))
for label in['baseline','candidate']:(c.scratch()/('metadata-'+label)).rename(c.scratch()/('historical-first-accounted-metadata-'+label))
