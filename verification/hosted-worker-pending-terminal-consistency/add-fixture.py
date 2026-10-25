from pathlib import Path
p=Path(__file__).resolve().parent/'candidate/test/worker.ts';s=p.read_text();needle="   case 'reviewMutation':"
fixture='''   case 'rememberTerminal':{
    this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS fixture_terminal_original(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)');
    this.ctx.storage.sql.exec('INSERT INTO fixture_terminal_original VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value',JSON.stringify(this.ledger.read()));await this.ledger.sync();return {ok:true};
   }
   case 'restoreTerminal':{
    const original=JSON.parse(this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM fixture_terminal_original WHERE singleton=1').toArray()[0]!.value) as Record<string,SqlStorageValue>;
    // Keys originate exclusively in our own remembered SQLite row, never caller input.
    const keys=Object.keys(original);this.ctx.storage.sql.exec('UPDATE operation SET '+keys.map(k=>k+'=?').join(','),...keys.map(k=>original[k]!));await this.ledger.sync();return {ok:true};
   }
   case 'terminalAckSyncMutation':{
    const original=this.ledger.sync.bind(this.ledger),storage=this.ctx.storage;
    this.ledger.sync=async()=>{this.ledger.sync=original;await original();storage.sql.exec("UPDATE operation SET phase=CASE phase WHEN 'stopped' THEN 'completed' ELSE 'stopped' END");await original();};return {ok:true};
   }
   case 'terminalMutation':{
    const r=this.ledger.read()!,o=r.track_outbox_json?JSON.parse(r.track_outbox_json):null;
    const opposite=r.phase==='stopped'?'completed':'stopped';
    switch(arg.field){
     case 'outboxPhase':o.terminal.phase=opposite;break;
     case 'rowPhase':this.ctx.storage.sql.exec('UPDATE operation SET phase=?',opposite);break;
     case 'rowAndOutboxPhase':this.ctx.storage.sql.exec('UPDATE operation SET phase=?',opposite);o.terminal.phase=opposite;break;
     case 'terminalStatus':{const t=JSON.parse(r.terminal_json!);t.status=opposite;this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?',JSON.stringify(t));break;}
     case 'missingTerminal':this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=NULL');break;
     case 'missingProjectionTerminal':o.terminal=null;break;
     case 'missingBothTerminal':this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=NULL');o.terminal=null;break;
     case 'pendingPhase':this.ctx.storage.sql.exec("UPDATE operation SET phase='stop_pending'");break;
     case 'terminalNextDue':this.ctx.storage.sql.exec("UPDATE operation SET next_due_us='1'");break;
     case 'projectionNextDue':o.nextDueUs='1';break;
     case 'malformedTerminal':this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='{' ");break;
     case 'terminalArray':this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='[]'");break;
     case 'terminalNull':this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='null'");break;
     case 'terminalUnknownStatus':this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?','{"status":"running"}');break;
     case 'terminalDuplicateStatus':this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?','{"status":"completed","status":"stopped","diagnostic_sha256":"'+'d'.repeat(64)+'"}');break;
     case 'terminalInvalidBody':this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?',JSON.stringify(r.phase==='completed'?{status:'completed',result:{outcome:'failed'}}:{status:'stopped',diagnostic_sha256:'invalid'}));break;
     case 'exactJsonMismatch':o.terminal.exactJson+=' ';break;
     case 'projectionFalse':o.terminal=false;break;
     case 'projectionMissingField':delete o.terminal;break;
     case 'malformedOutbox':this.ctx.storage.sql.exec("UPDATE operation SET track_outbox_json='{' ");await this.ledger.sync();return {ok:true};
     case 'missingOutbox':this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=NULL');await this.ledger.sync();return {ok:true};
     case 'unexpectedTerminal':o.terminal={phase:'stopped',exactJson:JSON.stringify({status:'stopped',diagnostic_sha256:'d'.repeat(64)})};break;
     case 'terminalPhaseWithoutEvidence':this.ctx.storage.sql.exec("UPDATE operation SET phase='stopped'");break;
     case 'malformedTerminalAndProvider':this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='{',provider_kind='external-macos'");break;
     default:throw new Error('terminal_mutation');
    }
    if(o!==null)this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?',JSON.stringify(o));await this.ledger.sync();return {ok:true};
   }
'''
assert needle in s;s=s.replace(needle,fixture+needle,1);p.write_text(s)
