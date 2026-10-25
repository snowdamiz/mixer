from pathlib import Path
p=Path(__file__).resolve().parent/'candidate/src/ledger.ts';s=p.read_text();s=s.replace('fence(identityBytes:string,version:string,reason:string):void{','fence(identityBytes:string,version:string,reason:string,preserveOperationRow=false):void{',1);s=s.replace('    const r=this.read();\n    // The independent fence is permanent', '    // Invalid restored terminal projections are evidence, not repair input.\n    // Keep their complete row/outbox unchanged, including below MAX and when\n    // terminal bytes cannot be parsed by save(). The independent fence wins.\n    if(preserveOperationRow)return;\n    const r=this.read();\n    // The independent fence is permanent',1);p.write_text(s)
p=Path(__file__).resolve().parent/'candidate/src/engine.ts';s=p.read_text();s=s.replace('Observation,result,sha,text,WireRequest','Observation,parseJSON,result,sha,text,WireRequest',1)
needle='  private trackSnapshotValid('
helper='''  // Synchronous validation of the current local projection, not merely its
  // equality with an earlier snapshot. Parse status from exact permanent bytes;
  // never normalize or repair those bytes before computing their evidence hash.
  private terminalProjection(r:Row):CoalescedTrackOutbox|null{
    let phase:'completed'|'stopped'|null=null;
    if(r.terminal_json!==null){
      if(typeof r.terminal_json!=='string')throw new Error('terminal_bytes');
      const terminal=parseJSON(new TextEncoder().encode(r.terminal_json),32768);
      if(!terminal||typeof terminal!=='object'||Array.isArray(terminal))throw new Error('terminal_shape');
      const observation=terminal as Record<string,unknown>;
      if(observation.status==='stopped'){exact(observation,['status','diagnostic_sha256']);hex(observation.diagnostic_sha256);phase='stopped';}
      else if(observation.status==='completed'){exact(observation,['status','result']);result(observation.result);phase='completed';}
      else throw new Error('terminal_status');
      if(r.phase!==phase||r.next_due_us!==null)throw new Error('terminal_row');
    }else if(r.phase==='completed'||r.phase==='stopped')throw new Error('terminal_missing');
    if(r.track_outbox_json===null){
      if(phase!==null&&BigInt(r.registry_ack_version)<BigInt(r.state_version))throw new Error('terminal_outbox_missing');
      return null;
    }
    const outbox=JSON.parse(r.track_outbox_json) as CoalescedTrackOutbox;
    registryExact(outbox,['stateVersion','nextDueUs','terminal']);registryDecimal(outbox.stateVersion);
    if(outbox.stateVersion!==r.state_version)throw new Error('outbox_version');
    if(phase===null){
      if(outbox.terminal!==null)throw new Error('unexpected_terminal');
      if(outbox.nextDueUs!==null)registryDecimal(outbox.nextDueUs);
    }else{
      registryExact(outbox.terminal,['phase','exactJson']);
      if(outbox.terminal.phase!==phase||outbox.terminal.exactJson!==r.terminal_json||outbox.nextDueUs!==null)throw new Error('terminal_outbox');
    }
    return outbox;
  }
  // Caller holds the synchronous ledger transaction. Preserve every recovery
  // byte on invalid projection; ordinary fence save() must not parse/replace it.
  private terminalConsistent(r:Row):boolean{
    try{this.terminalProjection(r);return true;}
    catch{this.ledger.fence(this.fenceIdentity(r),r.state_version,'track_terminal_inconsistent',true);return false;}
  }
'''
assert needle in s;s=s.replace(needle,helper+needle,1)
s=s.replace("    if(!this.providerMatches(current)){this.providerFenceInTransaction(current);return false;}","    if(!this.terminalConsistent(current))return false;\n    if(!this.providerMatches(current)){this.providerFenceInTransaction(current);return false;}",1)
s=s.replace("    const snapshot=this.ledger.read();if(!snapshot)return false;\n    if(!this.providerMatches(snapshot))", "    const snapshot=this.ledger.read();if(!snapshot)return false;\n    if(!this.ledger.transaction(current=>current!==null&&this.terminalConsistent(current))){await this.ledger.sync();return false;}\n    if(!this.providerMatches(snapshot))",1)
old="""      const outbox=JSON.parse(bytes) as CoalescedTrackOutbox;
      registryExact(outbox,['stateVersion','nextDueUs','terminal']);registryDecimal(outbox.stateVersion);
      if(outbox.stateVersion!==snapshot.state_version)throw new Error('outbox_version');"""
s=s.replace(old,"      const outbox=this.terminalProjection(snapshot)!;",1)
s=s.replace("        registryExact(outbox.terminal,['phase','exactJson']);\n        if(outbox.terminal.exactJson!==snapshot.terminal_json||!['completed','stopped'].includes(outbox.terminal.phase)||outbox.nextDueUs!==null)throw new Error('terminal_outbox');\n",'',1)
p.write_text(s)
