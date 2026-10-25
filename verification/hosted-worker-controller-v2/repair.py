#!/usr/bin/env python3
"""Apply the bounded R1/R2 repair only to the already verified candidate."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;P=HERE/'candidate/hosted-worker-controller'
p=P/'src/engine.ts';s=p.read_text()
s=s.replace('if(r&&i.upperUs<BigInt(r.clock_lower)){','if(r&&i.upperUs<BigInt(r.clock_floor)){')
s=s.replace('  private live(r:Row,i:Interval):boolean {','''  // Preserve the exact accepted interval separately from the maximum historical
  // lower bound. Overlapping uncertainty intervals may move the latest lower
  // bound backwards, but can never ratchet the historical bound backwards.
  // Callers save this with the decision in the same synchronous transaction.
  private acceptTime(r:Row,i:Interval):void {
    r.clock_lower=String(i.lowerUs);r.clock_upper=String(i.upperUs);r.clock_qualification=i.qualificationId;
    if(i.lowerUs>BigInt(r.clock_floor))r.clock_floor=String(i.lowerUs);
  }
  private live(r:Row,i:Interval):boolean {''')
s=s.replace('r.request_json=JSON.stringify(request);r.clock_lower=String(interval.lowerUs);r.clock_upper=String(interval.upperUs);r.clock_qualification=interval.qualificationId;','r.request_json=JSON.stringify(request);this.acceptTime(r,interval);')
s=s.replace('      const reuse=kind===r.effect_kind&&r.effect_state==="prepared";','      if(interval)this.acceptTime(r,interval);\n      const reuse=kind===r.effect_kind&&r.effect_state==="prepared";')
s=s.replace('      const interval=this.sample(r);return !!interval&&r.desired==="run"&&this.sameGuard(r,effect.request)&&this.live(r,interval);','''      const interval=this.sample(r);
      if(!interval||r.desired!=="run"||!this.sameGuard(r,effect.request)||!this.live(r,interval))return false;
      this.acceptTime(r,interval);this.ledger.save(r,"effect_time_accepted");return true;''')
s=s.replace('      if(r.quarantined)return;\n      if(effect.kind!=="stop"','      if(r.quarantined)return;\n      if(interval)this.acceptTime(r,interval);\n      if(effect.kind!=="stop"')
start=s.index('    const answer=this.ledger.transaction(r=>{',s.index('  async claim('));end=s.index('\n  async report(',start)
s=s[:start]+'''    const prospective=this.ledger.transaction(r=>{
      if(!r||r.quarantined||r.desired!=="run"||r.terminal_json||r.claim_state!=="unissued"||r.phase!=="inert")return null;
      if(claim.immutableSha256!==r.binding_hash||claim.identity.provider!==r.provider_kind||claim.identity.key!==r.provider_key||claim.identity.immutableSha256!==r.binding_hash||claim.instanceId!==r.instance_id||claim.bootId!==r.boot_id)return null;
      const i=this.sample(r);if(!i||!this.live(r,i))return null;
      this.acceptTime(r,i);
      r.claim_state="consumed";r.claim_id=uuid();r.phase="claim_consumed";this.ledger.save(r,"claim_consumed");
      return {operation_id:r.operation_id,binding:r.binding,binding_hash:r.binding_hash,
        epoch:r.epoch,revision:r.revision,owner:r.owner,expiry_us:r.expiry_us,
        provider_kind:r.provider_kind,provider_key:r.provider_key,instance_id:r.instance_id,boot_id:r.boot_id,claim_id:r.claim_id};
    });
    await this.ledger.sync();await this.hooks.point("after_claim_commit");
    // Consumption is already durable. This is the grant's linearization point,
    // after every await: compare the exact consumed authority and identity with
    // the current row, then accept the exact final qualified sample atomically.
    // No await follows this decision. The DO's default output gate confirms its
    // final clock-history write before the response becomes externally visible.
    return this.ledger.transaction(r=>{
      if(!prospective||!r||r.desired!=="run"||r.quarantined||r.terminal_json||r.claim_state!=="consumed"||r.phase!=="claim_consumed")return {granted:false};
      for(const key of Object.keys(prospective) as (keyof typeof prospective)[])if(r[key]!==prospective[key])return {granted:false};
      const i=this.sample(r);if(!i||!this.live(r,i))return {granted:false};
      this.acceptTime(r,i);this.ledger.save(r,"claim_grant_time_accepted");
      return {granted:true,claimId:prospective.claim_id};
    });
  }
''' + s[end:]
s=s.replace('      current.report_hash=hash;','      this.acceptTime(current,i);\n      current.report_hash=hash;')
p.write_text(s)
p=P/'src/ledger.ts';s=p.read_text().replace('clock_qualification:string;','clock_qualification:string;clock_floor:string;').replace('"clock_qualification","desired"','"clock_qualification","clock_floor","desired"')
s=s.replace('      storage.sql.exec(schema);\n      const versions=storage.sql.exec<{version:number}>("SELECT version FROM controller_schema").toArray();\n      if(versions.length!==1||versions[0]!.version!==1)throw new Error("schema_unavailable");','''      const exists=storage.sql.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='controller_schema'").toArray();
      if(exists.length){
        const versions=storage.sql.exec<{version:number}>("SELECT version FROM controller_schema").toArray();
        if(versions.length!==1||(versions[0]!.version!==1&&versions[0]!.version!==2))throw new Error("schema_unavailable");
        if(versions[0]!.version===1){
          storage.sql.exec("ALTER TABLE operation ADD COLUMN clock_floor TEXT NOT NULL DEFAULT '0'");
          storage.sql.exec("UPDATE operation SET clock_floor=clock_lower,quarantined=1");
          // V1 lost accepted time samples. Preserve all safety identity and stop/
          // claim/terminal fields, but never infer restored execution authority.
          storage.sql.exec("DROP TABLE controller_schema");
          storage.sql.exec("CREATE TABLE controller_schema(version INTEGER NOT NULL CHECK(version=2))");
          storage.sql.exec("INSERT INTO controller_schema(version) VALUES(2)");
        }
      }
      storage.sql.exec(schema);
      const versions=storage.sql.exec<{version:number}>("SELECT version FROM controller_schema").toArray();
      if(versions.length!==1||versions[0]!.version!==2)throw new Error("schema_unavailable");''')
s=s.replace('clock_qualification:clock.qualificationId,','clock_qualification:clock.qualificationId,clock_floor:String(clock.lowerUs),')
p.write_text(s)
p=P/'src/schema.sql';s=p.read_text().replace('CHECK(version=1)','CHECK(version=2)').replace('SELECT 1 WHERE NOT EXISTS','SELECT 2 WHERE NOT EXISTS').replace('clock_qualification TEXT NOT NULL,','clock_qualification TEXT NOT NULL, clock_floor TEXT NOT NULL,');p.write_text(s)
print('applied R1/R2 repair to isolated candidate')
