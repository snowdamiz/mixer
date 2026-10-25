import {DurableObject} from 'cloudflare:workers';
import {OperationState,Env} from './operation-state.js';
import {Engine} from './engine.js';
import {UnavailableClock} from './clock.js';
import {UnavailableObjectVerifier,UnavailableProvider} from './provider.js';
import type {PendingIdentity,RegistrationReceipt,WakeTicket,RecoveryDisposition,KnownOperationRecovery} from './public-contract.js';
export type {Env} from './operation-state.js';
export class MixerWorkerOperation extends DurableObject<Env> implements KnownOperationRecovery {
 #state:OperationState;
 constructor(ctx:DurableObjectState,env:Env){super(ctx,env);this.#state=new OperationState(ctx,env,(ledger,context)=>new Engine(ledger,new UnavailableClock(),new UnavailableProvider(),new UnavailableObjectVerifier(),undefined,context));}
 async fetch(request:Request):Promise<Response>{return this.#state.fetch(request);}
 async recoverKnown(i:PendingIdentity,p:RegistrationReceipt,t:WakeTicket):Promise<RecoveryDisposition>{return this.#state.recoverKnown(i,p,t);}
 async enrollExisting(i:PendingIdentity):Promise<'enrolled'|'missing'|'conflict'|'unavailable'>{return this.#state.enrollExisting(i);}
 async alarm():Promise<void>{await this.#state.alarm();}
}
