#!/usr/bin/env python3
"""Run only two remaining admission/error controls on exact source copies."""
import os
os.environ["REVIEW_RUN_ID"]="run-5"
import run_review as runner

def main():
 assert not runner.RUN.exists() and not runner.SCRATCH.exists()
 runner.SCRATCH.mkdir(parents=True)
 result={"status":"not-complete"}
 try:
  runner.run("compile-admission",[runner.RUSTC,"--edition=2021","-O","--test",runner.OUT/"source/analyzer.rs","--crate-name","independent_admission_review","-o",runner.SCRATCH/"tests"])
  for method in ["independent_setup_finish_admission_retains0_and534_before_cells","independent_allocator_helper_and_early_outer_limit_errors"]:
   runner.run(method,[runner.SCRATCH/"tests","--exact","fixture_envelope::tests::"+method,"--nocapture","--test-threads=1"],deadline=120)
  result={"status":"admission-followup-complete","scope":"two new exact-source methods only; original12 retained in run-3","selected_source":runner.info(runner.OUT/"source/envelope.rs"),"parent_source":runner.info(runner.OUT/"source/analyzer.rs"),"tests":runner.info(runner.OUT/"tests/envelope_tests.rs"),"runner":runner.info(runner.OUT/"run_review.py"),"followup":runner.info(runner.Path(__file__)),"rustc":runner.info(runner.RUSTC)}
 finally:
  runner.cleanup();runner.js(runner.OUT/"admission-followup-receipt.json",result)

if __name__=="__main__":main()
