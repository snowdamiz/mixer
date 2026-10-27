"""Child validates final inputs; owning runner seals only after terminal receipt."""
import json,sys
sys.dont_write_bytecode=True
from custody import HERE,roster,sha,need
import derive as D
import audit

def main():
 need(not(HERE/'seal.json').exists(),'one-time immutable correction packet')
 audit.main();before=roster();need(before==D.load(HERE/'input-lock.json'),'freeze before custody');after=roster();need(before==after,'freeze after custody')
 (HERE/'final-input-custody.json').write_text(json.dumps(after,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'freeze_preparation':'passed; runner writes full membership seal after child reaped/own group absent and command receipt complete','source146':D.TREE,'frozen_input_custody_sha256':sha(D.canon(after)),'no_compiler_or_native':True}))
if __name__=='__main__':main()
