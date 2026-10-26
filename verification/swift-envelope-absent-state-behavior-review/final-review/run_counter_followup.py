#!/usr/bin/env python3
"""Rerun only the counter overlay after fixing its fixture-root collision."""
import os
os.environ["REVIEW_RUN_ID"]="run-4"
import run_review as runner

def main():
 assert not runner.RUN.exists() and not runner.SCRATCH.exists()
 runner.SCRATCH.mkdir(parents=True)
 result={"status":"not-complete"}
 try:
  runner.run("compile-counter",[runner.RUSTC,"--edition=2021","-O","--test",runner.OUT/"instrumented/source/analyzer.rs","--crate-name","independent_counted_review","-o",runner.SCRATCH/"counter-tests"])
  runner.run("counter-tests",[runner.SCRATCH/"counter-tests","--nocapture","--test-threads=1"],deadline=120)
  result={"status":"counter-followup-complete","scope":"only test-only interposition controls; exact-source12 and API1+8 remain run-3 receipts","selected_source":runner.info(runner.OUT/"source/envelope.rs"),"instrumented_source":runner.info(runner.OUT/"instrumented/source/envelope.rs"),"counter_tests":runner.info(runner.OUT/"counter_tests.rs"),"runner":runner.info(runner.OUT/"run_review.py"),"followup":runner.info(runner.Path(__file__)),"rustc":runner.info(runner.RUSTC)}
 finally:
  runner.cleanup();runner.js(runner.OUT/"counter-followup-receipt.json",result)

if __name__=="__main__":main()
