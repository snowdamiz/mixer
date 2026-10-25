import {DurableObject} from "cloudflare:workers";
import {UnavailableClock} from "./clock.js";
import {Engine} from "./engine.js";
import {Ledger} from "./ledger.js";
import {ingress,operationKey,PrincipalEnv} from "./principal.js";
import {UnavailableObjectVerifier,UnavailableProvider} from "./provider.js";
import {errorResponse,reply} from "./wire.js";
export interface Env extends PrincipalEnv {OPERATIONS:DurableObjectNamespace}
export class MixerWorkerOperation extends DurableObject<Env> {
  private engine:Engine;
  constructor(ctx:DurableObjectState,env:Env){
    super(ctx,env);this.engine=new Engine(new Ledger(ctx.storage),new UnavailableClock(),new UnavailableProvider(),new UnavailableObjectVerifier());
    ctx.blockConcurrencyWhile(()=>this.engine.recover());
  }
  async fetch(request:Request):Promise<Response>{
    const checked=await ingress(request,this.env);if(checked instanceof Response)return checked;
    const {r}=checked;
    try{return reply(r,await this.engine.command(r,{provider:"unavailable",key:await operationKey(r),immutableSha256:r.immutable_sha256}));}
    catch{return errorResponse(400);}
  }
  async alarm():Promise<void>{await this.engine.alarm();}
}
