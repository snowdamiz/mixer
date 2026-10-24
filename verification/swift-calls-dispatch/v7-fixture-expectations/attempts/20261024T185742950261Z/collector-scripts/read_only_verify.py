"""Read-only review seal and full compiler accounting replay. No compiler or VM."""
import sys
sys.dont_write_bytecode=True
import collect as c
import final_accounting_report as report
from pathlib import Path

def main():
 seal=c.read_json(c.HERE/'review-seal.json');assert seal['runtimeQualified']is False and seal['independentAccountingAccepted']is False
 for rel,expected in seal['bindings'].items():
  data=(c.HERE/rel).read_bytes();assert len(data)==expected['bytes']and c.sha(data)==expected['sha256'],('sealed input drift',rel)
 assert c.sha(c.enc(c.manifest(c.HERE/'candidate')))==seal['candidateSourceClosure']
 assert c.sha(c.enc(c.manifest(c.HERE/'baseline')))==seal['baselineSourceClosure']
 before=c.manifest(c.HERE/'baseline');after=c.manifest(c.HERE/'candidate');changed={x for x in set(before)|set(after)if before.get(x)!=after.get(x)}
 assert changed==set(seal['allowedChangedCandidateFiles'])and len(after)==130 and len(before)==128
 for cfg,q in c.read_json(c.HERE/'final-query-bindings.json').items():
  assert q==c.read_json(c.HERE/f'exact-query-{cfg}.json')and q['sourceClosure']==seal['candidateSourceClosure']
 report.main(False)
 print('Read-only seal verification passed; no compiler/interpreter/native execution or acceptance granted')
if __name__=='__main__':main()
