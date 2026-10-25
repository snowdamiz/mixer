from pathlib import Path
p=Path(__file__).resolve().parent/'candidate/test/worker.ts'
s=p.read_text();at="   case 'independentValidShapeReport':{"
add="""   case 'migrationMutation':{
    switch(arg.field){
     case 'identityOnly':this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=?',JSON.stringify(this.identity));break;
     case 'receiptOnly':{const r=await new RegistryPort(this.env).register(this.identity);if(r.status!=='registered'&&r.status!=='duplicate')throw new Error('fixture_receipt');this.ctx.storage.sql.exec('UPDATE operation SET registration_json=?',JSON.stringify(r.receipt));break;}
     case 'emptyIdentity':this.ctx.storage.sql.exec(\"UPDATE operation SET pending_identity_json=''\");break;
     case 'emptyReceipt':this.ctx.storage.sql.exec(\"UPDATE operation SET registration_json=''\");break;
     case 'effectBarrier':this.ctx.storage.sql.exec(\"UPDATE operation SET effect_barrier_version='0'\");break;
     case 'claimBarrier':this.ctx.storage.sql.exec(\"UPDATE operation SET claim_barrier_version='0'\");break;
     case 'nonquarantined':this.ctx.storage.sql.exec('UPDATE operation SET quarantined=0');break;
     case 'ackPositive':this.ctx.storage.sql.exec(\"UPDATE operation SET registry_ack_version='1'\");break;
     case 'versionZero':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='0'\");break;
     case 'versionNoncanonical':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='01'\");break;
     case 'versionNegative':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='-1'\");break;
     case 'versionOverflow':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='9223372036854775808'\");break;
     case 'versionUnknown':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='unknown'\");break;
     case 'ackNoncanonical':this.ctx.storage.sql.exec(\"UPDATE operation SET registry_ack_version='00'\");break;
     case 'ackNegative':this.ctx.storage.sql.exec(\"UPDATE operation SET registry_ack_version='-1'\");break;
     case 'ackOverflow':this.ctx.storage.sql.exec(\"UPDATE operation SET registry_ack_version='9223372036854775808'\");break;
     case 'ackUnknown':this.ctx.storage.sql.exec(\"UPDATE operation SET registry_ack_version='unknown'\");break;
     case 'wrongProvider':this.ctx.storage.sql.exec(\"UPDATE operation SET provider_kind='external-macos'\");break;
     case 'wrongBinding':this.ctx.storage.sql.exec(\"UPDATE operation SET binding=binding||' '\");break;
     case 'changedOwner':this.ctx.storage.sql.exec(\"UPDATE operation SET owner='migration-race-owner'\");break;
     case 'changedIdentity':this.ctx.storage.sql.exec('UPDATE operation SET operation_id=?','f'.repeat(64));break;
     case 'fullRegistration':{const r=await new RegistryPort(this.env).register(this.identity);if(r.status!=='registered'&&r.status!=='duplicate')throw new Error('fixture_receipt');this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=?,registration_json=?',JSON.stringify(this.identity),JSON.stringify(r.receipt));break;}
     case 'regressAcknowledged':{const r=this.ledger.read()!;if(r.track_outbox_json!==null||r.registry_ack_version!==r.state_version||BigInt(r.state_version)<1n)throw new Error('exact_ack_required');this.ctx.storage.sql.exec('UPDATE operation SET state_version=?',String(BigInt(r.state_version)-1n));break;}
     case 'maxEqual':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='9223372036854775807',registry_ack_version='9223372036854775807',track_outbox_json=NULL\");break;
     case 'maxAhead':this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='9223372036854775806',registry_ack_version='9223372036854775807',track_outbox_json=NULL\");break;
     case 'maxAheadPending':{const r=this.ledger.read()!;this.ctx.storage.sql.exec(\"UPDATE operation SET state_version='9223372036854775806',registry_ack_version='9223372036854775807',track_outbox_json=?\",JSON.stringify({stateVersion:'9223372036854775806',nextDueUs:r.next_due_us,terminal:r.terminal_json?{phase:r.phase,exactJson:r.terminal_json}:null}));break;}
     case 'pendingAckLower':{const r=this.ledger.read()!;if(!r.track_outbox_json)throw new Error('pending_outbox_required');this.ctx.storage.sql.exec('UPDATE operation SET registry_ack_version=?',String(BigInt(r.state_version)-1n));break;}
     default:throw new Error('finite_migration_mutation');
    }await this.ledger.sync();return {ok:true};
   }
   case 'migrationEnrollmentHold':{const s=this.store.get();s.fault='before_existing_enrollment_register';s.blocked=false;this.store.set(s);return {ok:true};}
"""
assert at in s;s=s.replace(at,add+at)
# Hook belongs only to excluded fixture: delay registry registration after initial
# validation/hash so tests can mutate current SQLite state during an actual await.
s=s.replace("const result=await super.register(i);", "const result=await super.register(i);")
s=s.replace("registry:new RegistryPort(env)});", "registry:{register:async identity=>{await hooks.point('before_existing_enrollment_register');return new RegistryPort(env).register(identity);},track:input=>new RegistryPort(env).track(input)}});")
p.write_text(s)
