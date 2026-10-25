from pathlib import Path
p=Path(__file__).resolve().parent/'candidate/test/worker.ts'
s=p.read_text()
needle="   case 'rememberTerminal':{"
insert="""   case 'independentValidShapeReport':{
    const r=this.ledger.read()!;
    return {status:await this.engine.report({identity:this.ledger.identity(r),immutableSha256:r.binding_hash,instanceId:r.instance_id??'review-instance',bootId:r.boot_id??'review-boot',claimId:r.claim_id??'a'.repeat(32),operationId:r.operation_id,result:{outcome:'failed',class:'compiler',code:'compiler_error',diagnostic_sha256:'a'.repeat(64)},attestationSha256:'a'.repeat(64)})};
   }
   case 'independentAckAhead':{
    const r=this.ledger.read()!;if(r.track_outbox_json!==null||!r.terminal_json||BigInt(r.state_version)<2n)throw new Error('review_terminal_ack_required');
    this.ctx.storage.sql.exec('UPDATE operation SET state_version=?',String(BigInt(r.state_version)-1n));await this.ledger.sync();return {ok:true};
   }
   case 'independentTerminalBytes':{
    const r=this.ledger.read()!,o=JSON.parse(r.track_outbox_json!);let bytes:string;
    if(arg.kind==='validEscapedStatus')bytes=' {\\"diagnostic_sha256\\":\\"'+'d'.repeat(64)+'\\",\\"statu\\\\u0073\\":\\"stop\\\\u0070ed\\"}\\n';
    else if(arg.kind==='escapedDuplicate')bytes='{\\"status\\":\\"stopped\\",\\"statu\\\\u0073\\":\\"stopped\\",\\"diagnostic_sha256\\":\\"'+'d'.repeat(64)+'\\"}';
    else if(arg.kind==='extraTerminalField')bytes=JSON.stringify({...JSON.parse(r.terminal_json!),recovery:true});
    else if(arg.kind==='duplicateResult')bytes='{\\"status\\":\\"completed\\",\\"result\\":{\\"outcome\\":\\"failed\\",\\"class\\":\\"compiler\\",\\"code\\":\\"compiler_error\\",\\"code\\":\\"compiler_error\\",\\"diagnostic_sha256\\":\\"'+'a'.repeat(64)+'\\"}}';
    else if(arg.kind==='tooManyBytes')bytes=' '.repeat(32768)+r.terminal_json!;
    else throw new Error('review_terminal_case');
    o.terminal.exactJson=bytes;this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?,track_outbox_json=?',bytes,JSON.stringify(o));await this.ledger.sync();return {ok:true};
   }
   case 'independentPreserveFence':{
    const before=this.ledger.read();let rolledBack=false;
    try{this.ctx.storage.transactionSync(()=>{const r=this.ledger.read()!;this.ledger.fence('independent-review-identity',r.state_version,'independent_review_first',true);if(arg.rollback===true){this.ctx.storage.sql.exec(\"UPDATE operation SET owner='rollback-owner'\");throw new Error('review_rollback');}this.ledger.fence('replacement-identity','0','replacement-reason',true);});}catch(e){if((e as Error).message!=='review_rollback')throw e;rolledBack=true;}
    await this.ledger.sync();return {before,after:this.ledger.read(),rolledBack};
   }
"""
assert needle in s
p.write_text(s.replace(needle,insert+needle,1))
