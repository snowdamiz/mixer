#!/usr/bin/env python3
"""Seal source-only review evidence after a fresh guarded control replay."""
import offline
offline.install()
import datetime,difflib,json,sys
from pathlib import Path
import admit as a
import context_check as w

HERE=Path(__file__).resolve().parent


def write(name,value):
 (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def main():
 result=json.loads((HERE/'root-controls-result.json').read_bytes())
 a.need(result['status']=='passed'and result['testsRun']==43 and not any(result[n]for n in ('failures','errors','skipped')),'Fresh full control replay required')
 rows={n:a.file_row((HERE/n).read_bytes())for n in result['controlSourceFiles']}
 a.need(rows==result['controlSourceFiles']and a.closure(rows)==result['controlSourceTreeSHA256'],'Fresh controls source binding changed')
 parent=w.verify_parent();document=w.parse((HERE/'workflow.yml').read_text());original=w.parse((HERE/'historical/workflow.yml').read_text())
 context=w.validate_contract(document,original);manifest,data=a.inputs()
 a.need(not list(HERE.glob('pure-*')),'Pure-test scratch remains')
 historical=json.loads((HERE/'historical/source-basis.json').read_bytes())
 parent_seal=json.loads((HERE/'historical/seal.json').read_bytes())
 for name in ('admit.py','workflow.yml','root_controls.py'):
  before=(HERE/'historical'/name).read_text().splitlines(keepends=True)
  after=(HERE/name).read_text().splitlines(keepends=True)
  (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(before,after,fromfile=w.PARENT+name,tofile=w.SIBLING+name)))
 basis={'schema':1,'selected':False,'workflowInstalled':False,'parent':parent,
        'parentFiles':parent_seal['files'],'sourceRevisionParentSupplied':'836fc67b','sourceRevisionLocallyQueried':False,
        'correction':['Exact runner.temp Rustup home moved from job env to both install and driver step env',
                      'Exact x86_64-unknown-linux-gnu rustfmt-preview and clippy-preview membership',
                      'Sibling commands/artifacts and added sibling sparse path; parent retained for bindings'],
        'materializer':{'path':a.INPUT_HELPER,'sha256':a.INPUT_HELPER_SHA,'changed':False,'frozenMembersVerified':60,
                        'membersPerArm':136,'overlayPaths':list(a.OVERLAYS),'baselineTreeSHA256':a.BASELINE,'candidateTreeSHA256':a.CANDIDATE},
        'unchangedCommandPolicy':historical['commands'],'unchangedProvisioning':historical['provisioning'],
        'rawComponentManifestHashScope':'Raw bytes observation only; ordering is not a reproducibility identity',
        'controlSourceFiles':rows,'controlSourceTreeSHA256':a.closure(rows),
        'sources':[{'url':'https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability',
                    'observation':'jobs env excludes runner; step env includes runner; data-only excerpt in context-rules.json'},
                   {'url':'https://github.com/rust-lang/rustup/issues/4853',
                    'observation':'Rustup 1.29.0 example has exact Linux target-qualified component names and differing ordering'},
                   {'url':'https://raw.githubusercontent.com/rust-lang/rustup/1.28.2/src/dist/manifestation.rs',
                    'observation':'Tagged source explains installed component names may include target triple'}],
        'contextCheck':context,'sparseClosure':result['sparseClosure'],
        'semanticLifecycleResult':{'runID':40810326741,'source':'Parent supplied independently reviewed remote result; not queried by this lane',
                                   'cargoCommandsPassed':6,'debugPassed':690,'debugIgnored':9,'releasePassed':690,'releaseIgnored':9,
                                   'formattingOrLintEvidence':False},
        'pending':['Root independent review and explicit selection','Actual hosted tool installation, formatting and Clippy',
                   'Exact formatter artifact and baseline/candidate lint review','Canonical integration',
                   'Native/physical/published-package FieldLog and all GA gates']}
 write('source-basis.json',basis)
 receipt={'schema':1,'status':'43 guarded controls passed; host correction proposal unselected',
          'command':'python3 -B '+w.SIBLING+'root_controls.py','finalizationCommand':'python3 -B '+w.SIBLING+'finalize.py',
          'recordedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pythonVersion':sys.version,
          'sourceRevisionParentSupplied':'836fc67b','sourceRevisionLocallyQueried':False,
          'controlSourceFiles':rows,'controlSourceTreeSHA256':a.closure(rows),
          'output':{'path':'root-controls-result.json',**a.file_row((HERE/'root-controls-result.json').read_bytes())},
          'testsRun':result['testsRun'],'priorSemanticsReplayed':26,'newCorrectionControls':17,'errors':0,'failures':0,'skipped':0,
          'frozenParent':parent,'source':basis['materializer'],'sparseRequiredPaths':len(result['sparseClosure']['requiredPaths']),
          'historicalControlsInheritedAsCurrentEvidence':False,'officialValidatorExecuted':False,
          'scope':'guarded source/filesystem/mock replay only; no tool installation, actual formatting/lint, semantic runtime or live custody evidence',
          'actualLocalRustRuns':0,'toolInstallations':0,'hostedRuns':0,'selected':False,'workflowInstalled':False,
          'localGitGhUsed':False,'nativeUICaptureRuns':0,'processInventoryOrHeldProbes':0,
          'realNestedProcessSessionGroupSignalWaitSocketOperations':0,'liveCustodyEvidence':False,
          'onlyOwnedNewVerificationDirectoryWritten':True,'pureScratchRemaining':[],'GAQualified':False,
          'heldRemoteFieldLog':{'runID':40802230894,'pgid':2424,'pid':2621,'probed':False,'signalled':False,'disposalAssumed':False}}
 write('receipt.json',receipt)
 files={p.relative_to(HERE).as_posix():a.file_row(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()and p!=HERE/'seal.json'}
 a.need(not any(p.is_symlink()for p in HERE.rglob('*')),'No symlinks in packet')
 seal={'schema':1,'scope':'unselected source-only host context/component correction; no canonical workflow or remote attempt',
       'parentSealSHA256':w.PARENT_SEAL,'baselineSourceTreeSHA256':a.BASELINE,'candidateSourceTreeSHA256':a.CANDIDATE,
       'files':files,'treeSHA256':a.closure(files)}
 write('seal.json',seal)
 print(json.dumps({'status':receipt['status'],'files':len(files),'treeSHA256':seal['treeSHA256'],
                   'sealSHA256':a.digest((HERE/'seal.json').read_bytes()),'sparseRequiredPaths':receipt['sparseRequiredPaths']}))


if __name__=='__main__':main()
