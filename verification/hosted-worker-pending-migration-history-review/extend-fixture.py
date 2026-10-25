from pathlib import Path
p=Path(__file__).parent/'candidate/test/worker.ts'
s=p.read_text();anchor="   case 'migrationRecover':"
extra=r'''   case 'reviewDowngradeOnly':{
    const version=arg.version;if(version!==1&&version!==2)throw new Error('review_schema');
    this.ctx.storage.transactionSync(()=>{
      for(const field of ['pending_identity_json','registration_json','registry_ack_version','effect_barrier_version','claim_barrier_version','track_outbox_json'])this.ctx.storage.sql.exec('ALTER TABLE operation DROP COLUMN '+field);
      if(version===1)this.ctx.storage.sql.exec('ALTER TABLE operation DROP COLUMN clock_floor');
      this.ctx.storage.sql.exec('DROP TABLE registry_quarantine');this.ctx.storage.sql.exec('DROP TABLE controller_schema');
      this.ctx.storage.sql.exec('CREATE TABLE controller_schema(version INTEGER NOT NULL)');this.ctx.storage.sql.exec('INSERT INTO controller_schema VALUES(?)',version);
    });await this.ledger.sync();return {row:this.ctx.storage.sql.exec('SELECT * FROM operation').toArray()[0],version};
   }
   case 'reviewRestore':{
    switch(arg.scenario){
      case 'extraOutbox':{const r=this.ledger.read()!;this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?',JSON.stringify({stateVersion:r.state_version,nextDueUs:r.next_due_us,terminal:r.terminal_json===null?null:{phase:r.phase,exactJson:r.terminal_json}}));break;}
      case 'statePlus':this.ctx.storage.sql.exec("UPDATE operation SET state_version='+3'");break;
      case 'ackSpaces':this.ctx.storage.sql.exec("UPDATE operation SET registry_ack_version=' 0'");break;
      case 'stateFraction':this.ctx.storage.sql.exec("UPDATE operation SET state_version='3.0'");break;
      case 'quarantineTwo':this.ctx.storage.sql.exec('UPDATE operation SET quarantined=2');break;
      case 'ordinaryAhead':{const r=this.ledger.read()!;this.ctx.storage.sql.exec('UPDATE operation SET registry_ack_version=?,track_outbox_json=NULL',String(BigInt(r.state_version)+1n));break;}
      case 'maxAhead':this.ctx.storage.sql.exec("UPDATE operation SET state_version='9223372036854775806',registry_ack_version='9223372036854775807',track_outbox_json=NULL");break;
      case 'maxEqual':this.ctx.storage.sql.exec("UPDATE operation SET state_version='9223372036854775807',registry_ack_version='9223372036854775807',track_outbox_json=NULL");break;
      case 'rowFailureCount':this.ctx.storage.sql.exec('UPDATE operation SET failures=failures+1');break;
      case 'rowNextDue':this.ctx.storage.sql.exec("UPDATE operation SET next_due_us='1900000001000000'");break;
      case 'rowClockFloor':this.ctx.storage.sql.exec("UPDATE operation SET clock_floor='1899999999999998'");break;
      case 'delete':this.ctx.storage.sql.exec('DELETE FROM operation');break;
      case 'exactAlternateTerminal':{const r=this.ledger.read()!;const t=JSON.parse(r.terminal_json!);if(t.status==='stopped')t.diagnostic_sha256='e'.repeat(64);else t.result.diagnostic_sha256='e'.repeat(64);this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?',JSON.stringify(t));break;}
      case 'wrongProvider':this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='external-macos'");break;
      case 'newFence':this.ctx.storage.sql.exec("INSERT OR IGNORE INTO registry_quarantine VALUES(1,'review-fence','5','review_restore_fence')");break;
      default:throw new Error('finite_review_restore');
    }await this.ledger.sync();return {row:this.ledger.read()};
   }
'''
assert s.count(anchor)==1
p.write_text(s.replace(anchor,extra+anchor))
