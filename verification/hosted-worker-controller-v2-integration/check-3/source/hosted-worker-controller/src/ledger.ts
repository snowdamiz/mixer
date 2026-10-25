import schema from "./schema.sql";
import {Interval} from "./clock.js";
import {ResourceIdentity} from "./provider.js";
import {immutableBytes,MAX,WireRequest} from "./wire.js";
export interface Row {
  [key:string]:SqlStorageValue;
  singleton:number;operation_id:string;binding:string;binding_hash:string;request_json:string;
  epoch:string;revision:string;owner:string;expiry_us:string;clock_lower:string;clock_upper:string;clock_qualification:string;clock_floor:string;
  desired:"none"|"run"|"stop";phase:"unlaunched"|"launch_pending"|"inert"|"claim_consumed"|"running"|"stop_pending"|"completed"|"stopped"|"uncertain"|"quarantined";
  provider_key:string;provider_kind:ResourceIdentity["provider"];state_version:string;
  claim_state:"unissued"|"consumed"|"revoked";claim_id:string|null;instance_id:string|null;boot_id:string|null;
  effect_id:string|null;effect_request_json:string|null;effect_kind:"launch"|"inspect"|"stop"|null;effect_state:"none"|"prepared"|"dispatched"|"uncertain"|"settled";
  launch_dispatched:number;terminal_json:string|null;report_hash:string|null;pending_result_json:string|null;
  next_due_us:string|null;failures:number;quarantined:number;
}
const columns = ["singleton","operation_id","binding","binding_hash","request_json","epoch","revision","owner","expiry_us","clock_lower","clock_upper","clock_qualification","clock_floor","desired","phase","provider_key","provider_kind","state_version","claim_state","claim_id","instance_id","boot_id","effect_id","effect_request_json","effect_kind","effect_state","launch_dispatched","terminal_json","report_hash","pending_result_json","next_due_us","failures","quarantined"] as const;
// SQL templates derive only from this compile-time fixed identifier list.
const upsert=`INSERT INTO operation (${columns.join(",")}) VALUES (${columns.map(()=>"?").join(",")}) ON CONFLICT(singleton) DO UPDATE SET ${columns.filter(k=>k!=="singleton").map(k=>`${k}=excluded.${k}`).join(",")}`;
export class Ledger {
  constructor(readonly storage:DurableObjectStorage){
    storage.transactionSync(()=>{
      const exists=storage.sql.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='controller_schema'").toArray();
      if(exists.length){
        const versions=storage.sql.exec<{version:number}>("SELECT version FROM controller_schema").toArray();
        if(versions.length!==1||(versions[0]!.version!==1&&versions[0]!.version!==2))throw new Error("schema_unavailable");
        if(versions[0]!.version===1){
          storage.sql.exec("ALTER TABLE operation ADD COLUMN clock_floor TEXT NOT NULL DEFAULT '0'");
          const prior=this.read();
          if(prior){prior.clock_floor=prior.clock_lower;prior.quarantined=1;this.save(prior,"schema2_quarantine");}
          // V1 lost accepted time samples. Preserve all safety identity and stop/
          // claim/terminal fields, but never infer restored execution authority.
          storage.sql.exec("DROP TABLE controller_schema");
          storage.sql.exec("CREATE TABLE controller_schema(version INTEGER NOT NULL CHECK(version=2))");
          storage.sql.exec("INSERT INTO controller_schema(version) VALUES(2)");
        }
      }
      storage.sql.exec(schema);
      const versions=storage.sql.exec<{version:number}>("SELECT version FROM controller_schema").toArray();
      if(versions.length!==1||versions[0]!.version!==2)throw new Error("schema_unavailable");
    });
  }
  read():Row|null{return this.storage.sql.exec<Row>("SELECT * FROM operation WHERE singleton=1").toArray()[0]??null;}
  transaction<T>(fn:(r:Row|null)=>T):T{return this.storage.transactionSync(()=>fn(this.read()));}
  save(r:Row,kind:string):void {
    const n=BigInt(r.state_version)+1n;if(n>MAX)throw new Error("ledger_exhausted");r.state_version=String(n);
    this.storage.sql.exec(upsert,...columns.map(k=>r[k]));
    this.storage.sql.exec("INSERT INTO audit(sequence,kind,state_version) VALUES(?,?,?) ON CONFLICT(sequence) DO UPDATE SET kind=excluded.kind,state_version=excluded.state_version",Number(n%32n),kind,r.state_version);
  }
  initial(request:WireRequest,clock:Interval,identity:ResourceIdentity):Row {
    return {singleton:1,operation_id:request.operation_id,binding:immutableBytes(request),binding_hash:request.immutable_sha256,
      request_json:JSON.stringify(request),epoch:request.guard.epoch,revision:request.guard.revision,owner:request.guard.owner_id,expiry_us:request.guard.expires_at_us,
      clock_lower:String(clock.lowerUs),clock_upper:String(clock.upperUs),clock_qualification:clock.qualificationId,clock_floor:String(clock.lowerUs),
      desired:"none",phase:"unlaunched",provider_key:identity.key,provider_kind:identity.provider,state_version:"0",
      claim_state:"unissued",claim_id:null,instance_id:null,boot_id:null,effect_id:null,effect_request_json:null,effect_kind:null,effect_state:"none",launch_dispatched:0,
      terminal_json:null,report_hash:null,pending_result_json:null,next_due_us:null,failures:0,quarantined:0};
  }
  identity(r:Row):ResourceIdentity{return {provider:r.provider_kind,key:r.provider_key,immutableSha256:r.binding_hash};}
  async sync():Promise<void>{await this.storage.sync();}
}
