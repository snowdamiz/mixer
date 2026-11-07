import type {PendingIdentity,RegistrationReceipt,PendingRegistry} from './vendor/public-contract.js';
import {exact,identity,identityBytes,receipt,same} from './vendor/pending-types.js';
import type {Row} from './ledger.js';
import {immutableBytes,WireRequest} from './wire.js';
export interface RegistryContext {identity:PendingIdentity;registry:PendingRegistry}
export const unavailableRegistry:PendingRegistry={async register(){return {status:'unavailable'};},async track(){return {status:'unavailable'};}};
export async function checkedContext(context:RegistryContext|undefined,value:PendingIdentity,p:RegistrationReceipt):Promise<{identity:PendingIdentity;receipt:RegistrationReceipt;bytes:string}>{
 if(!context)throw new Error('registry_unavailable');
 const c={generation:context.identity.namespaceGeneration,operationsNamespace:'fixed-operation-binding',registryNamespace:'fixed-registry-binding'};
 const fixed=await identity(context.identity,c),i=await identity(value,c),r=receipt(p,c);
 if(fixed.bytes!==i.bytes||r.identityDigest!==i.digest||r.shard!==i.shard)throw new Error('registry_identity');
 return {identity:i.value,receipt:r,bytes:i.bytes};
}
export function matchesRequest(i:PendingIdentity,r:WireRequest):boolean{return i.environmentId===r.environment_id&&i.poolId===r.pool_id&&i.controllerId===r.controller_id&&i.platform===r.ref.platform&&i.operationId===r.operation_id&&i.immutableSha256===r.immutable_sha256;}
export function matchesRow(i:PendingIdentity,r:Row):boolean{
 try{const request=JSON.parse(r.request_json) as WireRequest;return matchesRequest(i,request)&&i.operationId===r.operation_id&&i.immutableSha256===r.binding_hash&&i.operationKey===r.provider_key&&immutableBytes(request)===r.binding;}catch{return false;}
}
export function retained(context:RegistryContext|undefined,r:Row):boolean{
 try{if(!context||!r.pending_identity_json||!r.registration_json)return false;const stored=JSON.parse(r.pending_identity_json);exact(stored,['namespaceGeneration','environmentId','poolId','controllerId','platform','operationKey','operationId','immutableSha256']);return identityBytes(stored as unknown as PendingIdentity)===identityBytes(context.identity)&&matchesRow(context.identity,r);}catch{return false;}
}
export {identityBytes,same};
