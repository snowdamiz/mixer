import type {PendingIdentity,RegistrationReceipt,Projection,RecoveryDisposition,WakeTicket} from './public-contract.js';
export const MAX=9223372036854775807n;
export const encoder=new TextEncoder();
export interface PendingConfig {generation:string;operationsNamespace:string;registryNamespace:string}
export interface PendingEnv {MIXER_PENDING_CONFIG?:string;PENDING_REGISTRY:DurableObjectNamespace;PENDING_AUDIT:DurableObjectNamespace;OPERATIONS:DurableObjectNamespace}
export function invalid():never{throw new Error('pending_invalid');}
export function exact(v:unknown,keys:readonly string[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))invalid();return v as Record<string,unknown>;}
export function hex(v:unknown,bits=256):string{if(typeof v!=='string'||v.length!==bits/4||!/^[0-9a-f]+$/.test(v))invalid();return v;}
export function decimal(v:unknown):string{if(typeof v!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(v)||BigInt(v)>MAX)invalid();return v;}
export function integer(v:unknown,min:number,max:number):number{if(typeof v!=='number'||!Number.isInteger(v)||v<min||v>max)invalid();return v;}
export function principal(v:unknown):string{if(typeof v!=='string'||v.length<1||v.length>128||!/^[\x20-\x7e]+$/.test(v))invalid();return v;}
export function config(env:PendingEnv):PendingConfig{const c=exact(JSON.parse(env.MIXER_PENDING_CONFIG??'null'),['generation','operationsNamespace','registryNamespace']);return {generation:hex(c.generation),operationsNamespace:principal(c.operationsNamespace),registryNamespace:principal(c.registryNamespace)};}
export function registryName(c:PendingConfig,index:number):string{return JSON.stringify(['mixer-worker-pending-registry-v1',c.generation,c.operationsNamespace,c.registryNamespace,integer(index,0,15)]);}
export function auditName(c:PendingConfig):string{return JSON.stringify(['mixer-worker-pending-audit-v1',c.generation,c.operationsNamespace,c.registryNamespace]);}
export const randomId=():string=>Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('');
export const sha=async(s:string):Promise<string>=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(s))),n=>n.toString(16).padStart(2,'0')).join('');
export function identityBytes(i:PendingIdentity):string{return JSON.stringify(['mixer-worker-pending-identity-v1',i.namespaceGeneration,i.environmentId,i.poolId,i.controllerId,i.platform,i.operationKey,i.operationId,i.immutableSha256]);}
export function identityFromBytes(s:string):PendingIdentity{const v=JSON.parse(s) as string[];return {namespaceGeneration:v[1]!,environmentId:v[2]!,poolId:v[3]!,controllerId:v[4]!,platform:v[5]! as 'ios'|'android',operationKey:v[6]!,operationId:v[7]!,immutableSha256:v[8]!};}
export async function identity(v:unknown,c:PendingConfig):Promise<{value:PendingIdentity;bytes:string;digest:string;shard:number}>{
 const p=exact(v,['namespaceGeneration','environmentId','poolId','controllerId','platform','operationKey','operationId','immutableSha256']);
 const i:PendingIdentity={namespaceGeneration:hex(p.namespaceGeneration),environmentId:principal(p.environmentId),poolId:principal(p.poolId),controllerId:principal(p.controllerId),platform:p.platform as 'ios'|'android',operationKey:hex(p.operationKey),operationId:hex(p.operationId),immutableSha256:hex(p.immutableSha256)};
 if(i.namespaceGeneration!==c.generation||!['ios','android'].includes(i.platform))invalid();
 const bytes=identityBytes(i);if(encoder.encode(bytes).length>2048)invalid();
 if(await sha(JSON.stringify(['mixer-worker-controller-do-v1',i.environmentId,i.poolId,i.controllerId,i.operationId]))!==i.operationKey)invalid();
 return {value:i,bytes,digest:await sha(bytes),shard:parseInt(i.operationKey[0]!,16)};
}
export function receipt(v:unknown,c:PendingConfig):RegistrationReceipt{const r=exact(v,['identityDigest','namespaceGeneration','recordId','shard','allocationIndex']);if(r.namespaceGeneration!==c.generation)invalid();return {identityDigest:hex(r.identityDigest),namespaceGeneration:hex(r.namespaceGeneration),recordId:hex(r.recordId,128),shard:integer(r.shard,0,15),allocationIndex:integer(r.allocationIndex,1,4096)};}
export function projection(v:unknown):Projection{if(!v||typeof v!=='object')invalid();const p=v as Record<string,unknown>;if(p.kind==='pending'){exact(p,['kind','nextDueUs']);return {kind:'pending',nextDueUs:p.nextDueUs===null?null:decimal(p.nextDueUs)};}exact(p,['kind','nextDueUs','phase','evidenceSha256']);if(p.kind!=='terminal'||p.nextDueUs!==null||!['completed','stopped'].includes(p.phase as string))invalid();return {kind:'terminal',nextDueUs:null,phase:p.phase as 'completed'|'stopped',evidenceSha256:hex(p.evidenceSha256)};}
export function ticket(v:unknown,c:PendingConfig):WakeTicket{const t=exact(v,['runId','wakeId','receipt','trackedVersion','attemptSequence']);return {runId:decimal(t.runId),wakeId:hex(t.wakeId,128),receipt:receipt(t.receipt,c),trackedVersion:decimal(t.trackedVersion),attemptSequence:decimal(t.attemptSequence)};}
export function disposition(v:unknown):RecoveryDisposition{if(!v||typeof v!=='object')invalid();const d=v as Record<string,unknown>;if(d.status==='pending'){exact(d,['status','stateVersion']);return {status:'pending',stateVersion:decimal(d.stateVersion)};}if(d.status==='terminal'){exact(d,['status','stateVersion','projection']);const p=projection(d.projection);if(p.kind!=='terminal')invalid();return {status:'terminal',stateVersion:decimal(d.stateVersion),projection:p};}exact(d,['status']);if(!['empty_orphan','quarantined','busy','unavailable','conflict'].includes(d.status as string))invalid();return {status:d.status} as RecoveryDisposition;}
export function same(a:unknown,b:unknown):boolean{return JSON.stringify(a)===JSON.stringify(b);}
export function next(v:string):string{const n=BigInt(decimal(v))+1n;if(n>MAX)throw new Error('pending_exhausted');return String(n);}
export async function wait<T>(promise:Promise<T>,ms:number):Promise<{ok:true;value:T}|{ok:false}>{let timer:ReturnType<typeof setTimeout>|undefined;try{return await Promise.race([promise.then(value=>({ok:true as const,value}),()=>({ok:false as const})),new Promise<{ok:false}>(resolve=>{timer=setTimeout(()=>resolve({ok:false}),ms);})]);}finally{if(timer!==undefined)clearTimeout(timer);}}
