from pathlib import Path
p=Path(__file__).resolve().parent/'candidate/src/engine.ts';s=p.read_text()
s=s.replace("private fence(bytes:string,version:string,reason:string):void{this.ledger.storage.transactionSync(()=>this.ledger.fence(bytes,version,reason));}","private fence(bytes:string,version:string,reason:string):void{this.ledger.storage.transactionSync(()=>{const current=this.ledger.read();if(current&&!this.terminalConsistent(current))return;this.ledger.fence(bytes,version,reason);});}",1)
# Guard synchronous mutation paths before provider fences and saves. Their
# original rejection values and committed nonterminal-stop permissions stay fixed.
for signature,ret in [("  private prepare():BarrierEffect|null {",'null'),("  private finalCheck(effect:BarrierEffect):boolean {",'false'),("  private accept(effect:BarrierEffect,raw:unknown):void {",''),("    const prospective=this.ledger.transaction(r=>{",'null')]:
 start=s.index(signature);pos=s.index('      if(r&&!this.providerMatches(r))',start);s=s[:pos]+f"      if(r&&!this.terminalConsistent(r))return{(' '+ret) if ret else ''};\n"+s[pos:]
start=s.index('  async claim(');pos=s.index('      if(r&&!this.providerMatches(r))',s.index('    return this.ledger.transaction(r=>{',start));s=s[:pos]+"      if(r&&!this.terminalConsistent(r))return {granted:false};\n"+s[pos:]
start=s.index('  async report(');pos=s.index('    if(r&&!this.providerMatches(r))',start);s=s[:pos]+"    if(r&&!this.ledger.transaction(current=>current!==null&&this.terminalConsistent(current))){await this.ledger.sync();return 'rejected';}\n"+s[pos:]
pos=s.index('      if(current&&!this.providerMatches(current))',start);s=s[:pos]+"      if(current&&!this.terminalConsistent(current))return false;\n"+s[pos:]
# Catch cleanup must not transform invalid projection evidence.
s=s.replace('this.ledger.transaction(r=>{if(r&&r.effect_id===id&&!r.terminal_json)', 'this.ledger.transaction(r=>{if(r&&!this.terminalConsistent(r))return;if(r&&r.effect_id===id&&!r.terminal_json)',1)
start=s.index('  async recoverKnown(')
for needle,name in [('      const r=this.ledger.read();','r'),('      const current=this.ledger.read();','current'),("      const after=this.ledger.read();if(!after)return {status:'unavailable'};",'after'),('        const last=this.ledger.read();','last')]:
 pos=s.index(needle,start)+len(needle);indent='        ' if name=='last' else '      ';s=s[:pos]+f"\n{indent}if({name}&&!this.ledger.transaction(row=>row!==null&&this.terminalConsistent(row))){{await this.ledger.sync();return {{status:'quarantined'}};}}"+s[pos:]
start=s.index('  async enrollExisting(');needle="    const prior=this.ledger.read();if(!prior)return 'missing';";pos=s.index(needle,start)+len(needle);s=s[:pos]+"\n    if(!this.ledger.transaction(current=>current!==null&&this.terminalConsistent(current))){await this.ledger.sync();return 'conflict';}"+s[pos:]
pos=s.index('        if(r&&!this.providerMatches(r))',start);s=s[:pos]+"        if(r&&!this.terminalConsistent(r))return false;\n"+s[pos:]
s=s.replace('this.ledger.transaction(r=>{if(r){r.quarantined=1;', 'this.ledger.transaction(r=>{if(r&&!this.terminalConsistent(r))return;if(r){r.quarantined=1;',1)
p.write_text(s)
