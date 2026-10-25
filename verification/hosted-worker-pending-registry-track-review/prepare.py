from pathlib import Path
import shutil,difflib,json,hashlib
root=Path(__file__).resolve().parents[2]; packet=Path(__file__).resolve().parent
source=root/'verification/hosted-worker-pending-registry-track-recheck/candidate'; target=packet/'candidate'
target.mkdir(exist_ok=True)
for f in ['src','test/worker.ts','test/harness.mjs','build.mjs','tsconfig.json']:
 s=source/f;t=target/f
 if s.is_dir():shutil.copytree(s,t,dirs_exist_ok=True)
 else:t.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(s,t)
p=target/'test/harness.mjs';p.write_text(p.read_text().replace('mixer-pending-track-recheck-owned-','mixer-pending-track-review-owned-'))
p=target/'test/worker.ts';before=p.read_text();needle="   case 'command':"
fixture="""   case 'reviewMutation':{
    switch(arg.field){
     case 'terminal_json':this.ctx.storage.sql.exec(\"UPDATE operation SET terminal_json=terminal_json||' '\");break;
     case 'phase':this.ctx.storage.sql.exec(\"UPDATE operation SET phase='completed'\");break;
     case 'versionOnly':{const r=this.ledger.read()!;this.ctx.storage.sql.exec('UPDATE operation SET state_version=?',String(BigInt(r.state_version)+1n));break;}
     case 'outboxPhase':{const r=this.ledger.read()!,o=JSON.parse(r.track_outbox_json!);o.terminal.phase='completed';this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?',JSON.stringify(o));break;}
     default:throw new Error('review_mutation');
    }await this.ledger.sync();return {ok:true};
   }
   case 'reviewAckSyncProviderChange':{
    const original=this.ledger.sync.bind(this.ledger),ledger=this.ledger,storage=this.ctx.storage;
    ledger.sync=async()=>{ledger.sync=original;await original();storage.sql.exec(\"UPDATE operation SET provider_kind='external-macos'\");await original();};return {ok:true};
   }
   case 'reviewAckGuard':{
    const r=this.ledger.read()!;let seen:unknown=null,threw=false,cleared=false;
    try{cleared=this.ledger.acknowledge(r.state_version,r.track_outbox_json!,current=>{
     seen=current;
     if(arg.mode==='throw'){this.ctx.storage.sql.exec(\"UPDATE operation SET provider_kind='external-macos'\");throw new Error('review_atomic_rollback');}
     if(arg.mode==='fence'){ledgerFence(this.ctx.storage,this.identity);return false;}
     return arg.mode==='allow';
    });}catch(e){if((e as Error).message!=='review_atomic_rollback')throw e;threw=true;}
    await this.ledger.sync();return {seen,threw,cleared};
   }
"""
fixture=fixture.replace('ledgerFence(this.ctx.storage,this.identity);',"this.ctx.storage.sql.exec(\"INSERT OR IGNORE INTO registry_quarantine VALUES(1,?,'0','review_ack_guard')\",JSON.stringify(this.identity));")
after=before.replace(needle,fixture+needle,1);p.write_text(after)
(packet/'fixture.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='frozen/test/worker.ts',tofile='review/test/worker.ts')))
print(json.dumps({'prepared':str(target),'productionSourceChanged':False,'addedFixtureActions':['reviewMutation','reviewAckSyncProviderChange','reviewAckGuard']}))
