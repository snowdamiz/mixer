"""Read-only V7/parent/history seal and complete final accounting replay."""
import sys,os
sys.dont_write_bytecode=True
import collect as c
import final_accounting_report as report

def bound(base,bindings):
 for rel,item in bindings.items():
  raw=(base/rel).read_bytes();assert len(raw)==item['bytes']and c.sha(raw)==item['sha256'],(str(base),rel,'sealed drift')
def main():
 seal=c.read_json(c.HERE/'review-seal.json');parent=c.HERE.parent;raw=(parent/'review-seal.json').read_bytes();assert c.sha(raw)==seal['parentSealSHA256'];p=c.read_json(parent/'review-seal.json');bound(parent,p['bindings']);assert (c.HERE/'parent-seal.json').read_bytes()==raw
 history=c.read_json(c.HERE/'v6-history-bindings.json');bound(c.HERE/history['path'],history['files']);bound(c.HERE,seal['bindings'])
 for item in c.read_json(c.HERE/'shared-evidence-links.json'):
  path=c.HERE/item['path'];assert path.is_symlink()and os.readlink(path)==item['target']and path.resolve()==(c.HERE/item['resolvedRelativePath']).resolve()
 before=c.manifest(c.HERE/'baseline');after=c.manifest(c.HERE/'candidate');assert len(before)==128 and len(after)==130;assert c.sha(c.enc(before))==seal['baselineSourceClosure']and c.sha(c.enc(after))==seal['candidateSourceClosure'];assert {x for x in set(before)|set(after)if before.get(x)!=after.get(x)}==set(seal['allowedChangedCandidateFiles'])
 accepted=c.manifest(parent/'candidate');delta={x for x in after if after[x]!=accepted[x]};assert delta==set(seal['selectedFixtureOnlyFiles'])
 for cfg,q in c.read_json(c.HERE/'final-query-bindings.json').items():assert q==c.read_json(c.HERE/f'exact-query-{cfg}.json')and q['sourceClosure']==seal['candidateSourceClosure']
 report.main(False)
 print('V7 read-only seal/parent/history/accounting replay passed; no compilation/VM/native execution or acceptance granted')
if __name__=='__main__':main()
